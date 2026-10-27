from datetime import timedelta, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4
import os
import time
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


def test_minio_real_signed_range_and_expiry():
    """Explicit local S3-compatible gate; the host owns the disposable bucket."""
    endpoint = os.environ.get("TEAQL_S3_TEST_ENDPOINT")
    bucket = os.environ.get("TEAQL_S3_TEST_BUCKET")
    access = os.environ.get("TEAQL_S3_TEST_ACCESS_KEY")
    secret = os.environ.get("TEAQL_S3_TEST_SECRET_KEY")
    if not all((endpoint, bucket, access, secret)):
        pytest.skip("explicit S3-compatible endpoint, bucket and credentials required")
    provider = S3ObjectStorage.connect(bucket, endpoint_url=endpoint,
        aws_access_key_id=access, aws_secret_access_key=secret)
    storage = UserContext().with_object_storage(provider).object_storage("F4 real S3-compatible Python")
    key = ObjectKey("f4/python/" + uuid4().hex)
    create_key = ObjectKey("f4/python/create/" + uuid4().hex)
    race_key = ObjectKey("f4/python/race/" + uuid4().hex)
    content = b"%PDF-1.7\nF4 real S3-compatible bytes\n%%EOF"
    try:
        written = storage.put_bytes(key, content, PutOptions(len(content), WriteMode.REPLACE, "application/pdf"))
        head = storage.head(key)
        assert head is not None and head.size == len(content)
        assert head.etag == written.etag and head.content_type == "application/pdf"
        assert storage.get_bytes(key, 1024) == content
        ticket = storage.get_read_url(key, ReadUrlOptions(timedelta(seconds=2), "attachment", "report.pdf"))
        # Do not log the signed URL or credentials.
        with urlopen(Request(ticket.url, headers={"Range": "bytes=0-7"}), timeout=5) as response:
            assert response.status == 206 and response.read() == content[:8]
            assert response.headers["Content-Type"] == "application/pdf"
            assert "report.pdf" in response.headers["Content-Disposition"]
        time.sleep(max(0, ticket.expires_at.timestamp() - time.time() + 1.3))
        with pytest.raises(HTTPError) as expired:
            urlopen(ticket.url, timeout=5)
        assert expired.value.code == 403
        if os.environ.get("TEAQL_S3_TEST_CREATE_ONLY") == "1":
            create = PutOptions(len(content), WriteMode.CREATE_ONLY, "application/pdf")
            created = storage.put_bytes(create_key, content, create)
            assert_error(StorageErrorCode.CONFLICT,
                         lambda: storage.put_bytes(create_key, b"x" * len(content), create))
            assert storage.head(create_key).etag == created.etag
            assert storage.get_bytes(create_key, 1024) == content
            candidates = (content, b"y" * len(content))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(storage.put_bytes, race_key, value, create)
                           for value in candidates]
                outcomes = []
                for future in futures:
                    try:
                        future.result()
                        outcomes.append("winner")
                    except StorageError as error:
                        assert error.code == StorageErrorCode.CONFLICT
                        outcomes.append("conflict")
            assert outcomes.count("winner") == outcomes.count("conflict") == 1
            assert storage.get_bytes(race_key, 1024) == candidates[outcomes.index("winner")]
    finally:
        try:
            storage.delete(key)
            if os.environ.get("TEAQL_S3_TEST_CREATE_ONLY") == "1":
                storage.delete(create_key)
                storage.delete(race_key)
        finally:
            provider.close()
