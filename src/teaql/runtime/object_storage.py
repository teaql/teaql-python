"""Synchronous binary stream facade; async applications can use asyncio.to_thread."""
from dataclasses import dataclass
from typing import Protocol, Optional, BinaryIO, Callable
from io import BytesIO
import logging
import time

from teaql.core.object_storage import (
    ObjectKey, ObjectMetadata, ObjectContent, PutOptions, ReadUrlOptions,
    ObjectReadUrl, StorageError, StorageErrorCode,
)
from .telemetry import RuntimeOperation, start_runtime_operation


@dataclass(frozen=True)
class StorageInvocation:
    context: object
    comment: str


class ObjectStorageProvider(Protocol):
    def put(self, invocation: StorageInvocation, key: ObjectKey, content: BinaryIO, options: PutOptions) -> ObjectMetadata: ...
    def get(self, invocation: StorageInvocation, key: ObjectKey) -> ObjectContent: ...
    def head(self, invocation: StorageInvocation, key: ObjectKey) -> Optional[ObjectMetadata]: ...
    def delete(self, invocation: StorageInvocation, key: ObjectKey) -> None: ...
    def get_read_url(self, invocation: StorageInvocation, key: ObjectKey, options: ReadUrlOptions) -> ObjectReadUrl: ...


@dataclass(frozen=True)
class StorageEvent:
    operation: str
    comment: str
    trace_id: str
    outcome: str
    elapsed_ms: float


class _Receipt:
    def __init__(self, invocation, operation):
        self.invocation, self.operation = invocation, operation
        self.started, self.ended = time.monotonic(), False
        self.scope = start_runtime_operation(invocation.context.runtime_telemetry(), RuntimeOperation("object_storage", operation))
        self.scope.activate()

    def detach(self):
        self.scope.deactivate()

    def finish(self, outcome):
        if self.ended:
            return
        self.ended = True
        self.detach()
        if outcome == "success":
            self.scope.success()
        else:
            self.scope.failure(StorageError(StorageErrorCode.IO if outcome == "cancelled" else StorageErrorCode(outcome)))
        safe = lambda text: "".join(" " if ord(c) < 32 or 127 <= ord(c) <= 159 else c for c in str(text or ""))
        event = StorageEvent(self.operation, safe(self.invocation.comment), safe(self.invocation.context.trace_id()),
                             outcome, (time.monotonic() - self.started) * 1000)
        observer = self.invocation.context.get_resource("object_storage_observer")
        try:
            if observer:
                observer(event)
            else:
                logging.getLogger("teaql.object_storage").warning(
                    "ObjectStorage operation=%s comment=%s trace=%s outcome=%s elapsedMs=%.3f",
                    event.operation, event.comment, event.trace_id, event.outcome, event.elapsed_ms)
        except Exception:
            pass


class _ObservedStream:
    def __init__(self, stream, size, receipt):
        self._stream, self._remaining, self._receipt = stream, size, receipt
        self._closed, self._ended = False, False

    @property
    def closed(self):
        return self._closed

    def read(self, size=-1):
        if self._closed:
            raise StorageError(StorageErrorCode.IO)
        if size == 0:
            return b""
        if self._ended:
            return b""
        error = None
        try:
            data = self._stream.read(size)
            if not isinstance(data, bytes) or len(data) > self._remaining or (not data and self._remaining != 0):
                error = StorageError(StorageErrorCode.IO)
            else:
                self._remaining -= len(data)
                # An unbounded read consumes to EOF in Python's BinaryIO contract.
                if not data or size < 0:
                    if self._remaining:
                        error = StorageError(StorageErrorCode.IO)
                    else:
                        self._ended = True
                        self._receipt.finish("success")
        except Exception:
            error = StorageError(StorageErrorCode.IO)
        if error:
            self._receipt.finish(error.code.value)
            self._close_raw()
            raise error
        return data

    def _close_raw(self):
        self._closed = True
        try:
            self._stream.close()
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        error = None
        try:
            self._stream.close()
        except Exception:
            error = StorageError(StorageErrorCode.IO)
        self._receipt.finish(error.code.value if error else "cancelled")
        if error:
            raise error

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self):
        return "ObjectStream[masked]"


class ObjectStorage:
    def __init__(self, context, comment):
        if not isinstance(comment, str) or not comment.strip():
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        self._provider = context.get_resource("object_storage_provider")
        if self._provider is None:
            raise StorageError(StorageErrorCode.NOT_CONFIGURED)
        self._invocation = StorageInvocation(context, comment)

    def _call(self, operation, work):
        receipt = _Receipt(self._invocation, operation)
        try:
            result = work()
            receipt.finish("success")
            return result
        except StorageError as error:
            receipt.finish(error.code.value)
            raise
        except Exception:
            receipt.finish(StorageErrorCode.UNAVAILABLE.value)
        raise StorageError(StorageErrorCode.UNAVAILABLE)

    def put(self, key: ObjectKey, content: BinaryIO, options: PutOptions):
        def work():
            error, result = None, None
            try:
                result = self._provider.put(self._invocation, key, content, options)
            except StorageError as caught:
                error = caught
            except Exception:
                error = StorageError(StorageErrorCode.UNAVAILABLE)
            try:
                content.close()
            except Exception:
                error = error or StorageError(StorageErrorCode.IO)
            if error:
                raise error
            return result
        return self._call("put", work)

    def put_bytes(self, key, content: bytes, options):
        return self.put(key, BytesIO(content), options)

    def get(self, key):
        receipt = _Receipt(self._invocation, "get")
        try:
            response = self._provider.get(self._invocation, key)
            receipt.detach()
            return ObjectContent(response.metadata, _ObservedStream(response.stream, response.metadata.size, receipt))
        except StorageError as error:
            receipt.finish(error.code.value)
            raise
        except Exception:
            receipt.finish(StorageErrorCode.UNAVAILABLE.value)
        raise StorageError(StorageErrorCode.UNAVAILABLE)

    def get_bytes(self, key, maximum_bytes: int):
        if type(maximum_bytes) is not int or maximum_bytes < 0:
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        with self.get(key) as content:
            if content.metadata.size > maximum_bytes:
                raise StorageError(StorageErrorCode.TOO_LARGE)
            result = bytearray()
            while True:
                block = content.stream.read(min(65536, maximum_bytes - len(result) + 1))
                if not block:
                    break
                if len(result) + len(block) > maximum_bytes:
                    raise StorageError(StorageErrorCode.TOO_LARGE)
                result.extend(block)
            return bytes(result)

    def head(self, key):
        return self._call("head", lambda: self._provider.head(self._invocation, key))

    def exists(self, key):
        return self.head(key) is not None

    def delete(self, key):
        return self._call("delete", lambda: self._provider.delete(self._invocation, key))

    def delete_if_version(self, key, content_version: str):
        if (not isinstance(content_version, str) or not content_version
                or len(content_version) > 256 or content_version == "*"
                or content_version.strip() != content_version
                or any(ord(char) < 32 or 127 <= ord(char) <= 159
                       for char in content_version)):
            raise StorageError(StorageErrorCode.INVALID_INPUT)
        conditional = getattr(self._provider, "delete_if_version", None)
        if not callable(conditional):
            raise StorageError(StorageErrorCode.UNSUPPORTED)
        def delete():
            result = conditional(self._invocation, key, content_version)
            if result not in ("deleted", "already_missing", "version_mismatch"):
                raise StorageError(StorageErrorCode.UNAVAILABLE)
            return result
        return self._call("delete_if_version", delete)

    def supports_version_conditional_delete(self) -> bool:
        return callable(getattr(self._provider, "delete_if_version", None))

    def get_read_url(self, key, options=ReadUrlOptions()):
        return self._call("read_url", lambda: self._provider.get_read_url(self._invocation, key, options))
