import threading
from teaql.runtime.telemetry_queue import ExportQueue


def fixture(capacity=4):
    lost = []
    return ExportQueue('traces', capacity, lambda signal, amount, reason: lost.append((signal, amount, reason))), lost


def test_failed_handoff_releases_capacity_and_is_not_accepted_prefix():
    queue, lost = fixture(1)
    def broken():
        raise RuntimeError('private enqueue error')
    queue.handoff(object(), broken)
    assert queue.snapshot()['admitted'] == queue.snapshot()['outstanding'] == 0
    assert queue.snapshot()['handoff_failed'] == 1
    assert queue.wait_prefix(queue.prefix(), .01)
    assert lost == [('traces', 1, 'handoff_failure')]


def test_later_completion_cannot_satisfy_older_prefix():
    queue, lost = fixture()
    first, second = object(), object()
    queue.handoff(first, lambda: None)
    target = queue.prefix()
    queue.handoff(second, lambda: None)
    queue.begin_export([second])(False)
    assert not queue.wait_prefix(target, .01)
    queue.begin_export([first])(False)
    assert queue.wait_prefix(target, .01) and not lost


def test_retirement_is_separate_from_active_failed_attempt_and_once_only():
    queue, lost = fixture()
    first, second = object(), object()
    for record in (first, second):
        queue.handoff(record, lambda: None)
    ticket = queue.begin_export([first])
    queue.abort_queued()
    queue.abort_queued()
    assert queue.snapshot()['retired'] == 1 and queue.snapshot()['exporting'] == 1
    assert queue.begin_export([second]) is None
    ticket(True)
    ticket(True)
    snapshot = queue.snapshot()
    assert snapshot['admitted'] == snapshot['completed'] + snapshot['retired'] == 2
    assert snapshot['outstanding'] == snapshot['exporting'] == 0
    assert lost == [('traces', 1, 'shutdown'), ('traces', 1, 'export_failure')]


def test_identity_is_not_inferred_from_equal_record_data():
    class Equal:
        def __eq__(self, other):
            return True
    queue, lost = fixture()
    admitted, other = Equal(), Equal()
    queue.handoff(admitted, lambda: None)
    assert queue.begin_export([other]) is None
    assert not queue.wait_prefix(queue.prefix(), .01)
    queue.begin_export([admitted])(False)
    assert queue.wait_idle(.01) and not lost


def test_concurrent_admission_is_exact_and_drop_does_not_call_sdk():
    queue, lost = fixture(128)
    submitted = []
    def offer():
        for _ in range(100):
            record = object()
            queue.handoff(record, lambda: submitted.append(record))
    threads = [threading.Thread(target=offer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    snapshot = queue.snapshot()
    assert snapshot['offered'] == 800
    assert snapshot['admitted'] == snapshot['outstanding'] == len(submitted) == 128
    assert snapshot['overflow'] == sum(amount for _, amount, _ in lost) == 672


def test_close_rejects_new_handoff_and_explicit_late_completion():
    queue, lost = fixture()
    queue.close()
    queue.handoff(object(), lambda: (_ for _ in ()).throw(AssertionError('must not call SDK')))
    queue.reject_late()
    assert queue.snapshot()['post_shutdown'] == 2
    assert queue.snapshot()['admitted'] == queue.snapshot()['outstanding'] == 0
    assert lost == [('traces', 1, 'shutdown'), ('traces', 1, 'shutdown')]


def test_duplicate_record_cannot_replace_an_accepted_ticket():
    queue, lost = fixture()
    record = object()
    queue.handoff(record, lambda: None)
    queue.handoff(record, lambda: (_ for _ in ()).throw(AssertionError('duplicate SDK enqueue')))
    assert queue.snapshot()['admitted'] == queue.snapshot()['outstanding'] == 1
    assert queue.snapshot()['handoff_failed'] == 1
    queue.begin_export([record])(False)
    assert queue.snapshot()['completed'] == 1
    assert lost == [('traces', 1, 'handoff_failure')]
