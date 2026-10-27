"""Optional private file store with an explicitly started authenticated local HTTP gateway."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock, Thread
from urllib.parse import urlsplit
import base64
import json
import os
import re
import secrets
import stat
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from teaql.core.object_storage import (
    ObjectContent, ObjectMetadata, ObjectReadUrl, StorageError, StorageErrorCode, WriteMode,
)


def _error(code):
    return StorageError(code)


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value):
    if not isinstance(value, str) or len(value) > 4096 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error):
        return None
    return decoded if _b64(decoded) == value else None


class FileObjectStorage:
    """The host must protect root and its parent; old generations require explicit GC."""

    def __init__(self, root, signing_key: bytes):
        try:
            path = Path(root)
        except TypeError:
            raise _error(StorageErrorCode.INVALID_INPUT) from None
        if not path.is_absolute() or not isinstance(signing_key, bytes) or len(signing_key) != 32:
            raise _error(StorageErrorCode.INVALID_INPUT)
        self._root = path
        self._cipher = AESGCM(signing_key)
        self._lock = RLock()
        self._server = None
        self._thread = None
        self._base_url = None

    def _private_root(self, create=False):
        if create:
            try:
                self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
            except OSError:
                raise _error(StorageErrorCode.IO) from None
        try:
            info = self._root.lstat()
        except OSError:
            raise _error(StorageErrorCode.UNAVAILABLE) from None
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
            raise _error(StorageErrorCode.UNAVAILABLE)

    def _directory(self, key_hash):
        return self._root / key_hash[:2] / key_hash

    @staticmethod
    def _hash(key):
        return sha256(key.value.encode("utf-8")).hexdigest()

    def _manifest(self, key_hash):
        try:
            raw = (self._directory(key_hash) / "manifest.json").read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            raise _error(StorageErrorCode.UNAVAILABLE) from None
        if len(raw) > 16384:
            raise _error(StorageErrorCode.UNAVAILABLE)
        try:
            value = json.loads(raw)
            version = value["version"]
            if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32}", version) or \
                    type(value["size"]) is not int or not 0 <= value["size"] <= 5 * 1024**3 or \
                    not isinstance(value["content_type"], str) or not value["content_type"] or \
                    not all(32 <= ord(c) <= 126 for c in value["content_type"]) or \
                    not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) or \
                    not isinstance(value["modified"], str) or not isinstance(value["metadata"], dict):
                raise ValueError("invalid manifest")
            datetime.fromisoformat(value["modified"])
        except (ValueError, TypeError, KeyError):
            raise _error(StorageErrorCode.UNAVAILABLE) from None
        return value

    def _metadata(self, key, manifest):
        return ObjectMetadata(key, manifest["size"], manifest["content_type"],
                              manifest["sha256"] + "." + manifest["version"],
                              datetime.fromisoformat(manifest["modified"]), manifest["metadata"])

    def _data_path(self, key_hash, manifest):
        return self._directory(key_hash) / ("data-" + manifest["version"])

    def _check_data(self, key_hash, manifest):
        try:
            info = self._data_path(key_hash, manifest).stat()
        except OSError:
            raise _error(StorageErrorCode.UNAVAILABLE) from None
        if not stat.S_ISREG(info.st_mode) or info.st_size != manifest["size"]:
            raise _error(StorageErrorCode.UNAVAILABLE)

    def put(self, invocation, key, content, options):
        self._private_root(create=True)
        key_hash = self._hash(key)
        directory = self._directory(key_hash)
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            raise _error(StorageErrorCode.IO) from None
        version = _b64(secrets.token_bytes(24))
        data_path = directory / ("data-" + version)
        temp_path = directory / ("manifest-" + version)
        published = False
        try:
            digest = sha256()
            size = 0
            with data_path.open("xb") as output:
                while True:
                    try:
                        block = content.read(65536)
                    except Exception:
                        raise _error(StorageErrorCode.IO) from None
                    if not isinstance(block, bytes) or len(block) > options.size - size:
                        raise _error(StorageErrorCode.INVALID_INPUT)
                    if not block:
                        break
                    output.write(block)
                    digest.update(block)
                    size += len(block)
                if size != options.size:
                    raise _error(StorageErrorCode.INVALID_INPUT)
                output.flush()
                os.fsync(output.fileno())
            manifest = dict(version=version, size=size, content_type=options.content_type,
                            sha256=digest.hexdigest(), modified=datetime.now(timezone.utc).isoformat(),
                            metadata=dict(options.metadata))
            with temp_path.open("xb") as output:
                output.write(json.dumps(manifest, separators=(",", ":")).encode("utf-8"))
                output.flush()
                os.fsync(output.fileno())
            destination = directory / "manifest.json"
            if options.mode == WriteMode.CREATE_ONLY:
                try:
                    os.link(temp_path, destination)
                except FileExistsError:
                    raise _error(StorageErrorCode.CONFLICT) from None
                published = True
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                os.replace(temp_path, destination)
                published = True
            return self._metadata(key, manifest)
        except StorageError:
            raise
        except OSError:
            raise _error(StorageErrorCode.IO) from None
        finally:
            if not published:
                for path in (data_path, temp_path):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass

    def get(self, invocation, key):
        self._private_root()
        key_hash = self._hash(key)
        manifest = self._manifest(key_hash)
        if manifest is None:
            raise _error(StorageErrorCode.NOT_FOUND)
        try:
            stream = self._data_path(key_hash, manifest).open("rb")
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != manifest["size"]:
                stream.close()
                raise _error(StorageErrorCode.UNAVAILABLE)
        except OSError:
            raise _error(StorageErrorCode.UNAVAILABLE) from None
        return ObjectContent(self._metadata(key, manifest), stream)

    def head(self, invocation, key):
        self._private_root()
        key_hash = self._hash(key)
        manifest = self._manifest(key_hash)
        if manifest is None:
            return None
        self._check_data(key_hash, manifest)
        return self._metadata(key, manifest)

    def delete(self, invocation, key):
        self._private_root()
        try:
            (self._directory(self._hash(key)) / "manifest.json").unlink(missing_ok=True)
        except OSError:
            raise _error(StorageErrorCode.IO) from None

    def _seal(self, ticket):
        nonce = secrets.token_bytes(12)
        payload = json.dumps(ticket, separators=(",", ":")).encode("utf-8")
        return _b64(nonce + self._cipher.encrypt(nonce, payload, None))

    def _open_ticket(self, token):
        raw = _unb64(token)
        if raw is None or len(raw) < 29:
            return None
        try:
            value = json.loads(self._cipher.decrypt(raw[:12], raw[12:], None))
            if not isinstance(value, dict) or not isinstance(value.get("hash"), str) or \
                    not re.fullmatch(r"[0-9a-f]{64}", value["hash"]) or \
                    not isinstance(value.get("version"), str) or \
                    not re.fullmatch(r"[A-Za-z0-9_-]{32}", value["version"]) or \
                    type(value.get("expires_ms")) is not int or \
                    value["expires_ms"] <= time.time_ns() // 1_000_000 or \
                    not (value.get("disposition") is None or isinstance(value["disposition"], str) and
                         all(32 <= ord(c) <= 126 for c in value["disposition"])):
                return None
        except Exception:
            return None
        return value

    def get_read_url(self, invocation, key, options):
        with self._lock:
            base = self._base_url
        if base is None:
            raise _error(StorageErrorCode.NOT_CONFIGURED)
        self._private_root()
        key_hash = self._hash(key)
        manifest = self._manifest(key_hash)
        if manifest is None:
            raise _error(StorageErrorCode.NOT_FOUND)
        self._check_data(key_hash, manifest)
        expires_at = datetime.now(timezone.utc) + options.lifetime
        ticket = self._seal(dict(hash=key_hash, version=manifest["version"],
                                 expires_ms=int(expires_at.timestamp() * 1000),
                                 disposition=options.content_disposition()))
        return ObjectReadUrl(base + "/objects/" + ticket, expires_at)

    def start(self):
        with self._lock:
            if self._server is not None:
                raise _error(StorageErrorCode.CONFLICT)
            self._private_root(create=True)
            owner = self

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    owner._serve(self, head=False)

                def do_HEAD(self):
                    owner._serve(self, head=True)

                def do_POST(self):
                    self.send_error(405)

                do_PUT = do_POST
                do_DELETE = do_POST

                def log_message(self, *_):
                    pass  # The path contains a private read ticket.

            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            except OSError:
                raise _error(StorageErrorCode.UNAVAILABLE) from None
            server.daemon_threads = True
            thread = Thread(target=server.serve_forever, daemon=True)
            self._server, self._thread = server, thread
            self._base_url = f"http://127.0.0.1:{server.server_port}"
            thread.start()
            return self._base_url

    def close(self):
        with self._lock:
            server, thread = self._server, self._thread
            self._server = self._thread = self._base_url = None
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _serve(self, handler, head):
        path = urlsplit(handler.path).path
        token = path.removeprefix("/objects/") if path.startswith("/objects/") else ""
        ticket = self._open_ticket(token)
        if ticket is None:
            handler.send_error(404)
            return
        try:
            manifest = self._manifest(ticket["hash"])
            if manifest is None or manifest["version"] != ticket["version"]:
                handler.send_error(404)
                return
            data_path = self._data_path(ticket["hash"], manifest)
            with data_path.open("rb") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size != manifest["size"]:
                    handler.send_error(404)
                    return
                size, start, end = manifest["size"], 0, manifest["size"] - 1
                range_header = handler.headers.get("Range")
                partial = range_header is not None
                if partial:
                    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
                    if not match or size == 0 or not any(match.groups()) or \
                            any(len(part) > 20 for part in match.groups()):
                        handler.send_response(416)
                        handler.send_header("Content-Range", f"bytes */{size}")
                        handler.end_headers()
                        return
                    first, last = match.groups()
                    if first:
                        start = int(first)
                        if last:
                            end = int(last)
                    else:
                        suffix = int(last)
                        start = max(0, size - suffix)
                    if start >= size or end < start or not first and int(last) == 0:
                        handler.send_response(416)
                        handler.send_header("Content-Range", f"bytes */{size}")
                        handler.end_headers()
                        return
                    end = min(end, size - 1)
                handler.send_response(206 if partial else 200)
                handler.send_header("Content-Type", manifest["content_type"])
                handler.send_header("Content-Length", str(end - start + 1 if partial else size))
                handler.send_header("Accept-Ranges", "bytes")
                handler.send_header("Cache-Control", "private, no-store")
                handler.send_header("X-Content-Type-Options", "nosniff")
                handler.send_header("ETag", '"' + manifest["sha256"] + "." + manifest["version"] + '"')
                if ticket["disposition"]:
                    handler.send_header("Content-Disposition", ticket["disposition"])
                if partial:
                    handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                handler.end_headers()
                if not head and size:
                    source.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = source.read(min(65536, remaining))
                        if not block:
                            break
                        handler.wfile.write(block)
                        remaining -= len(block)
        except (OSError, StorageError):
            if not handler.wfile.closed:
                try:
                    handler.send_error(404)
                except OSError:
                    pass

    def __repr__(self):
        return "FileObjectStorage[configuration=masked]"
