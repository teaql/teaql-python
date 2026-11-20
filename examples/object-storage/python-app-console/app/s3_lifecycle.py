"""Local-source S3 lifecycle fixture. Test bucket creation is administration."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
from uuid import uuid4
import os
import time
import urllib.request
import urllib.error
import boto3
from botocore.config import Config
from teaql.core.object_storage import *
from teaql.runtime import UserContext
from teaql.provider.s3 import S3ObjectStorage


def expect(code, work):
    try:
        work()
    except StorageError as error:
        assert error.code == code, (error.code, code)
        return
    raise AssertionError(f"expected {code}")


def main():
    bucket = os.environ["TEAQL_S3_BUCKET"]
    client = boto3.client("s3", endpoint_url=os.environ["TEAQL_S3_ENDPOINT"], region_name="us-east-1",
        aws_access_key_id=os.environ["TEAQL_S3_ACCESS_KEY"], aws_secret_access_key=os.environ["TEAQL_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 1}, s3={"addressing_style": "path"}))
    from botocore.exceptions import ClientError
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
            raise RuntimeError("test bucket setup failed") from None
        client.create_bucket(Bucket=bucket)
    provider = S3ObjectStorage(client, bucket)
    events = []
    context = UserContext().with_trace_id("storage-example").with_object_storage(provider).with_object_storage_observer(events.append)
    storage = context.object_storage("verify binary object storage")
    prefix = f"python-example/{uuid4().hex}/"
    key = ObjectKey(prefix + "收据 +% binary")
    empty, race = ObjectKey(prefix + "empty"), ObjectKey(prefix + "race")
    data = bytes(i % 251 for i in range(256 * 1024))
    try:
        assert not storage.exists(key)
        expect(StorageErrorCode.NOT_FOUND, lambda: storage.get(key))
        options = PutOptions(len(data), WriteMode.CREATE_ONLY, "application/octet-stream", {"example": "binary"})
        storage.put_bytes(key, data, options)
        metadata = storage.head(key)
        assert metadata.size == len(data) and metadata.custom_metadata["example"] == "binary" and metadata.etag
        assert storage.get_bytes(key, len(data)) == data
        expect(StorageErrorCode.CONFLICT, lambda: storage.put_bytes(key, b"", PutOptions(0, WriteMode.CREATE_ONLY)))
        expect(StorageErrorCode.TOO_LARGE, lambda: storage.get_bytes(key, 1))
        url = storage.get_read_url(key, ReadUrlOptions(disposition="attachment", filename="receipt.bin"))
        with urllib.request.urlopen(url.url, timeout=5) as response:
            assert response.read() == data
            assert response.headers["Content-Disposition"] == 'attachment; filename="receipt.bin"'
        expires = storage.get_read_url(key, ReadUrlOptions(timedelta(seconds=1)))
        time.sleep(2.2)
        try:
            urllib.request.urlopen(expires.url, timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("expired URL must be denied")
        storage.put_bytes(empty, b"", PutOptions(0, WriteMode.CREATE_ONLY))
        assert storage.get_bytes(empty, 0) == b""
        expect(StorageErrorCode.INVALID_INPUT, lambda: storage.put_bytes(key, b"ab", PutOptions(1, WriteMode.REPLACE)))
        assert storage.get_bytes(key, len(data)) == data
        storage.put_bytes(key, b"new", PutOptions(3, WriteMode.REPLACE))
        assert storage.get_bytes(key, 3) == b"new"
        other = UserContext().with_trace_id("storage-other").with_object_storage(provider).with_object_storage_observer(events.append)
        def create(api):
            try:
                api.put_bytes(race, b"race", PutOptions(4, WriteMode.CREATE_ONLY))
                return "success"
            except StorageError as error:
                assert error.code == StorageErrorCode.CONFLICT
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, [storage, other.object_storage("verify atomic create")]))
        assert sorted(results) == ["conflict", "success"]
        assert {e.trace_id for e in events} == {"storage-example", "storage-other"}
        missing = UserContext().with_object_storage(S3ObjectStorage(client, "missing-" + uuid4().hex))
        expect(StorageErrorCode.UNAVAILABLE, lambda: missing.object_storage("verify missing bucket").exists(key))
        for item in (key, empty, race):
            storage.delete(item)
            storage.delete(item)
            assert not storage.exists(item)
        assert prefix not in repr(events) and "X-Amz-Signature" not in repr(events)
        print("PASS Python S3: binary, empty, metadata, URL download/expiry, atomic create, replace, bounded reads, missing bucket, repeated delete")
    finally:
        for item in (key, empty, race):
            storage.delete(item)
        provider.close()


if __name__ == "__main__":
    main()
