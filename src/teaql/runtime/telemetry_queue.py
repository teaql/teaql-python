"""Exact, bounded SDK-record admission; no replacement SDK batching queue."""
import threading
from time import monotonic


class _Admission:
    def __init__(self, record):
        self.record = record
        self.sequence = None
        self.state = 'queued'


class ExportQueue:
    def __init__(self, signal, capacity, on_loss):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('invalid-queue-capacity')
        self.signal, self.capacity, self.on_loss = signal, capacity, on_loss
        self.condition = threading.Condition(threading.RLock())
        self.pending = {}
        self.offered = self.admitted = self.completed = self.overflow = 0
        self.post_shutdown = self.handoff_failed = self.retired = 0
        self.closed = self.aborted = False

    def _lost(self, amount, reason):
        if amount:
            try:
                self.on_loss(self.signal, amount, reason)
            except Exception:
                pass

    def handoff(self, record, submit):
        reason = None
        with self.condition:
            self.offered += 1
            if self.closed:
                self.post_shutdown += 1
                reason = 'shutdown'
            elif len(self.pending) >= self.capacity:
                self.overflow += 1
                reason = 'queue_overflow'
            elif id(record) in self.pending:
                self.handoff_failed += 1
                reason = 'handoff_failure'
            else:
                key = id(record)
                admission = _Admission(record)
                self.pending[key] = admission
                try:
                    submit()
                    self.admitted += 1
                    admission.sequence = self.admitted
                    if admission.state == 'complete':
                        self.completed += 1
                except Exception:
                    self.pending.pop(key, None)
                    self.handoff_failed += 1
                    reason = 'handoff_failure'
                self.condition.notify_all()
        if reason:
            self._lost(1, reason)

    def begin_export(self, records):
        with self.condition:
            if self.aborted:
                return None
            admissions = [self.pending.get(id(record)) for record in records]
            if any(item is None or item.record is not record or item.state != 'queued'
                   for item, record in zip(admissions, records)):
                return None
            for item in admissions:
                item.state = 'exporting'
        completed = False
        def complete(failed):
            nonlocal completed
            settled = 0
            with self.condition:
                if completed:
                    return
                completed = True
                for item in admissions:
                    if self.pending.pop(id(item.record), None) is not item:
                        continue
                    item.state = 'complete'
                    settled += 1
                    if item.sequence is not None:
                        self.completed += 1
                if failed:
                    self._lost(settled, 'export_failure')
                self.condition.notify_all()
        return complete

    def prefix(self):
        with self.condition:
            return self.admitted

    def wait_prefix(self, target, timeout):
        deadline = monotonic() + timeout
        with self.condition:
            while any(item.sequence is not None and item.sequence <= target for item in self.pending.values()):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return True

    def wait_idle(self, timeout):
        deadline = monotonic() + timeout
        with self.condition:
            while self.pending:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return True

    def close(self):
        with self.condition:
            self.closed = True

    def abort_queued(self):
        with self.condition:
            if self.aborted:
                return
            self.aborted = True
            retired = [key for key, item in self.pending.items() if item.state == 'queued']
            for key in retired:
                self.pending.pop(key).state = 'retired'
            self.retired += len(retired)
            self.condition.notify_all()
        self._lost(len(retired), 'shutdown')

    def reject_late(self):
        with self.condition:
            self.offered += 1
            self.post_shutdown += 1
        self._lost(1, 'shutdown')

    def snapshot(self):
        with self.condition:
            return {'offered': self.offered, 'admitted': self.admitted, 'completed': self.completed,
                    'outstanding': len(self.pending), 'exporting': sum(item.state == 'exporting' for item in self.pending.values()),
                    'overflow': self.overflow, 'post_shutdown': self.post_shutdown,
                    'handoff_failed': self.handoff_failed, 'retired': self.retired}


class AdmissionBatchProcessor:
    """Wrap the SDK's already-snapshotted record handoff, not mutable log input."""
    def __init__(self, delegate, queue):
        self.delegate, self.queue = delegate, queue

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def emit(self, record):
        self.queue.handoff(record, lambda: self.delegate.emit(record))
