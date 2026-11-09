"""SQLite commit errors retain their identity and finish live rollback first."""
import asyncio
import sqlite3

import pytest

from teaql.provider.sqlite.transport import _SqliteTransaction


class Connection:
    def __init__(self, failure=None, rollback_failure=None, close_failure=None):
        self.failure, self.rollback_failure, self.close_failure = failure, rollback_failure, close_failure
        self.calls = []

    async def commit(self):
        self.calls.append('commit')
        if self.failure is not None:
            raise self.failure

    async def rollback(self):
        self.calls.append('rollback')
        if self.rollback_failure is not None:
            raise self.rollback_failure

    async def close(self):
        self.calls.append('close')
        if self.close_failure is not None:
            raise self.close_failure


@pytest.mark.asyncio
async def test_deferred_commit_failure_rolls_back_live_connection_and_cleanup_is_idempotent():
    error = sqlite3.IntegrityError('FOREIGN KEY constraint failed')
    db = Connection(error)
    transaction = _SqliteTransaction(db, lambda values: values, lambda value: value)
    with pytest.raises(sqlite3.IntegrityError) as caught:
        await transaction.commit_sql()
    assert caught.value is error
    assert db.calls == ['commit', 'rollback', 'close']
    await transaction.rollback_sql()
    assert db.calls == ['commit', 'rollback', 'close']


@pytest.mark.asyncio
@pytest.mark.parametrize('cleanup', ['rollback', 'close'])
async def test_cleanup_failure_cannot_replace_original_commit_failure(cleanup):
    error = sqlite3.IntegrityError('original commit error')
    extra = RuntimeError('cleanup error')
    db = Connection(error, extra if cleanup == 'rollback' else None, extra if cleanup == 'close' else None)
    transaction = _SqliteTransaction(db, lambda values: values, lambda value: value)
    with pytest.raises(sqlite3.IntegrityError) as caught:
        await transaction.commit_sql()
    assert caught.value is error and db.calls == ['commit', 'rollback', 'close']
    await transaction.rollback_sql()
    assert db.calls == ['commit', 'rollback', 'close']


@pytest.mark.asyncio
async def test_cancelled_commit_also_rolls_back_without_losing_cancellation():
    error = asyncio.CancelledError()
    db = Connection(error)
    transaction = _SqliteTransaction(db, lambda values: values, lambda value: value)
    with pytest.raises(asyncio.CancelledError) as caught:
        await transaction.commit_sql()
    assert caught.value is error and db.calls == ['commit', 'rollback', 'close']


@pytest.mark.asyncio
async def test_successful_commit_closes_once_without_a_later_rollback():
    db = Connection()
    transaction = _SqliteTransaction(db, lambda values: values, lambda value: value)
    await transaction.commit_sql()
    await transaction.rollback_sql()
    assert db.calls == ['commit', 'close']
