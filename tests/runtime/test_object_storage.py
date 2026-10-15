from datetime import timedelta, datetime, timezone
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
import boto3
from botocore.config import Config
from teaql.core.object_storage import *
from teaql.runtime import UserContext
from teaql.provider.s3 import S3ObjectStorage


class Stub:
    size = 3
    code = None
    seen = None
    def head(self, invocation, key):
        self.seen = invocation
        if self.code:
            raise StorageError(self.code)
        return None
    def put(self, invocation, key, stream, options):
        self.seen = invocation
        return ObjectMetadata(key, options.size)
    def get(self, invocation, key):
        return ObjectContent(ObjectMetadata(key, self.size), BytesIO(b"abc"))


def assert_error(code, work):
    with pytest.raises(StorageError) as found:
        work()
    assert found.value.code == code
    assert found.value.__cause__ is None
    assert "CANARY" not in str(found.value)
    return found.value


def test_object_storage_context_and_error_semantics():
    assert_error(StorageErrorCode.NOT_CONFIGURED, lambda: UserContext().object_storage("read"))
    stub = Stub()
    context = UserContext().with_object_storage(stub)
    assert_error(StorageErrorCode.INVALID_INPUT, lambda: context.object_storage("  "))
    storage = context.object_storage("read attachment")
    key = ObjectKey("PRIVATE-KEY-CANARY")
    assert not storage.exists(key)
    assert stub.seen.context is context
    assert stub.seen.comment == "read attachment"
    for code in (StorageErrorCode.ACCESS_DENIED, StorageErrorCode.UNAVAILABLE):
        stub.code = code
        assert_error(code, lambda: storage.exists(key))


def test_object_storage_stream_bounds_ownership_and_completion():
    events, stub = [], Stub()
    storage = UserContext().with_object_storage(stub).with_object_storage_observer(events.append).object_storage("read attachment")
    key = ObjectKey("PRIVATE-KEY-CANARY")
    stream = BytesIO(b"")
    storage.put(key, stream, PutOptions(0, WriteMode.CREATE_ONLY))
    assert stream.closed
    with storage.get(key) as response:
        assert response.stream.read(1) == b"a"
    assert events[-1].outcome == "cancelled"
    assert storage.get_bytes(key, 3) == b"abc"
    assert events[-1].outcome == "success"
    assert_error(StorageErrorCode.TOO_LARGE, lambda: storage.get_bytes(key, 2))
    for size in (2, 4):
        stub.size = size
        assert_error(StorageErrorCode.IO, lambda: storage.get_bytes(key, 5))
    assert "CANARY" not in repr(events)
    context = UserContext().with_object_storage(stub).with_object_storage_observer(lambda event: 1/0)
    assert not context.object_storage("read").exists(key)


def test_object_storage_options_and_private_representations():
    for value in ("", "a" * 1025, "bad\nkey", "\ud800"):
        assert_error(StorageErrorCode.INVALID_INPUT, lambda: ObjectKey(value))
    assert_error(StorageErrorCode.TOO_LARGE, lambda: PutOptions(MAX_PUT_SIZE + 1, WriteMode.CREATE_ONLY))
    assert_error(StorageErrorCode.INVALID_INPUT, lambda: PutOptions(0, WriteMode.CREATE_ONLY, "bad\r\nheader"))
    assert_error(StorageErrorCode.INVALID_INPUT, lambda: PutOptions(0, WriteMode.CREATE_ONLY, metadata={"Bad Key": "value"}))
    for seconds in (0, -1, 0.5, 604801):
        assert_error(StorageErrorCode.INVALID_INPUT, lambda: ReadUrlOptions(timedelta(seconds=seconds)))
    assert_error(StorageErrorCode.INVALID_INPUT, lambda: ReadUrlOptions(filename="bad\nname", disposition="attachment"))
    assert "CANARY" not in repr(ObjectKey("PRIVATE-KEY-CANARY"))
    assert "CANARY" not in repr(ObjectReadUrl("PRIVATE-URL-CANARY", None))
    options = PutOptions(0, WriteMode.CREATE_ONLY, metadata={"tag": "PRIVATE-METADATA-CANARY"})
    assert "CANARY" not in repr(options)
    with pytest.raises(TypeError):
        options.metadata["tag"] = "changed"
    class Signer:
        url = "https://example.invalid/?X-Amz-Date=20261015T000000Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host"
        def generate_presigned_url(self, *_args, **_kwargs):
            return self.url
    signer = Signer()
    storage = UserContext().with_object_storage(S3ObjectStorage(signer, "bucket")).object_storage("verify signed URL deadline")
    assert storage.get_read_url(ObjectKey("key")).expires_at == datetime(2026, 10, 15, 0, 5, tzinfo=timezone.utc)
    signer.url = "https://example.invalid/permanent"
    assert_error(StorageErrorCode.UNAVAILABLE, lambda: storage.get_read_url(ObjectKey("key")))


def test_object_storage_real_sdk_http_errors_are_not_absence():
    state = {"status": 403, "calls": 0}
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            state["calls"] += 1
            status = 200 if self.path.rstrip("/") == "/bucket" and state["status"] == 404 else state["status"]
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = boto3.client("s3", endpoint_url=f"http://127.0.0.1:{server.server_port}",
        aws_access_key_id="test", aws_secret_access_key="secret", region_name="us-east-1",
        config=Config(signature_version="s3v4", retries={"max_attempts": 0}, connect_timeout=0.2,
                      read_timeout=0.2, s3={"addressing_style": "path"}))
    provider = S3ObjectStorage(client, "bucket")
    storage = UserContext().with_object_storage(provider).object_storage("verify HTTP error semantics")
    key = ObjectKey("PRIVATE-KEY-CANARY")
    try:
        for status, expected in ((403, StorageErrorCode.ACCESS_DENIED), (500, StorageErrorCode.UNAVAILABLE),
            (503, StorageErrorCode.UNAVAILABLE), (408, StorageErrorCode.TIMEOUT),
            (504, StorageErrorCode.TIMEOUT), (501, StorageErrorCode.UNSUPPORTED)):
            state["status"] = status
            error = assert_error(expected, lambda: storage.exists(key))
            assert error.__context__ is None
        state["status"] = 404
        assert not storage.exists(key)
        state["status"] = 200
        assert_error(StorageErrorCode.UNAVAILABLE, lambda: storage.exists(key))
        before = state["calls"]
        for content, size in ((b"ab", 1), (b"a", 2)):
            assert_error(StorageErrorCode.INVALID_INPUT, lambda: storage.put_bytes(key, content, PutOptions(size, WriteMode.CREATE_ONLY)))
        class FailingInput(BytesIO):
            def read(self, *_):
                raise OSError("PRIVATE-INPUT-CANARY")
        stream = FailingInput()
        assert_error(StorageErrorCode.IO, lambda: storage.put(key, stream, PutOptions(1, WriteMode.CREATE_ONLY)))
        assert stream.closed
        assert state["calls"] == before
        server.shutdown()
        server.server_close()
        assert_error(StorageErrorCode.UNAVAILABLE, lambda: storage.exists(key))
    finally:
        server.shutdown()
        server.server_close()
        provider.close()
