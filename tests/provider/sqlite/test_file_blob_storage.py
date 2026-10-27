"""Real local File/HTTP behavior for the independent optional wheel."""
from datetime import timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import hashlib
import os
import time

import pytest

from teaql_blob_reference import FileObjectStorage
from teaql.core.object_storage import (
    ObjectKey, PutOptions, ReadUrlOptions, StorageError, StorageErrorCode, WriteMode,
)
from teaql.runtime import UserContext


def _status(url, *, method="GET", headers=None):
    try:
        with urlopen(Request(url, method=method, headers=headers or {}), timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as error:
        return error.code, dict(error.headers), error.read()


def test_file_storage_exact_bytes_and_authenticated_http(tmp_path):
    provider = FileObjectStorage(tmp_path / "objects", os.urandom(32))
    context = UserContext().with_object_storage(provider).with_object_storage_observer(lambda event: None)
    store = context.object_storage("verify real optional file store")
    key = ObjectKey("objects/PRIVATE-PYTHON-CANARY")
    content = b"%PDF-1.7\nTeaQL document\n%%EOF"
    try:
        with pytest.raises(StorageError) as unstarted:
            store.get_read_url(key)
        assert unstarted.value.code == StorageErrorCode.NOT_CONFIGURED
        assert provider.start().startswith("http://127.0.0.1:")
        options = PutOptions(len(content), WriteMode.CREATE_ONLY, "application/pdf")
        metadata = store.put_bytes(key, content, options)
        assert metadata.etag == hashlib.sha256(content).hexdigest()
        assert store.head(key).size == len(content)
        assert store.get_bytes(key, len(content)) == content
        with pytest.raises(StorageError) as conflict:
            store.put_bytes(key, content, options)
        assert conflict.value.code == StorageErrorCode.CONFLICT
        with pytest.raises(StorageError):
            store.put_bytes(key, content, PutOptions(len(content) + 1, WriteMode.REPLACE))
        assert store.get_bytes(key, len(content)) == content

        signed = store.get_read_url(key, ReadUrlOptions(timedelta(seconds=2), "attachment", "asset.pdf"))
        assert key.value not in signed.url and "PRIVATE-PYTHON-CANARY" not in repr(signed)
        code, headers, body = _status(signed.url)
        assert code == 200 and body == content
        assert headers["Content-Type"] == "application/pdf"
        assert headers["Content-Disposition"] == 'attachment; filename="asset.pdf"'
        assert headers["Cache-Control"] == "private, no-store"
        code, headers, body = _status(signed.url, method="HEAD")
        assert code == 200 and body == b"" and headers["Content-Length"] == str(len(content))
        code, headers, body = _status(signed.url, headers={"Range": "bytes=0-3"})
        assert code == 206 and body == content[:4]
        assert headers["Content-Range"] == f"bytes 0-3/{len(content)}"
        code, _, body = _status(signed.url, headers={"Range": "bytes=-3"})
        assert code == 206 and body == content[-3:]
        assert _status(signed.url, headers={"Range": "bytes=999-"})[0] == 416

        tampered = signed.url.replace("/objects/", "/objects/A", 1)
        assert _status(tampered)[0] == 404
        replacement = b"next generation"
        store.put_bytes(key, replacement, PutOptions(len(replacement), WriteMode.REPLACE))
        assert _status(signed.url)[0] == 404
        assert store.get_bytes(key, len(replacement)) == replacement
        expiring = store.get_read_url(key, ReadUrlOptions(timedelta(seconds=1)))
        time.sleep(1.1)
        assert _status(expiring.url)[0] == 404
        current = provider._manifest(provider._hash(key))
        provider._data_path(provider._hash(key), current).unlink()
        with pytest.raises(StorageError) as missing:
            store.head(key)
        assert missing.value.code == StorageErrorCode.UNAVAILABLE
        store.delete(key)
        assert not store.exists(key)
    finally:
        provider.close()
