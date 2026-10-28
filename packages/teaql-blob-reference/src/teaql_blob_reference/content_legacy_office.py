"""Optional Linux sandboxed binary DOC/XLS verifier for Blob uploads."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
import os
import signal
import stat
import subprocess
import sys

from .content_office import OfficeBlobContentVerifier
from .upload_service import BlobVerifiedContent


_MIME = {"doc": "application/msword", "xls": "application/vnd.ms-excel"}
_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")


def _u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _valid_container(data: bytes) -> bool:
    if (len(data) < 1024 or not data.startswith(_MAGIC)
            or _u16(data, 28) != 0xfffe or _u16(data, 32) != 6):
        return False
    major, shift = _u16(data, 26), _u16(data, 30)
    if not ((major, shift) in ((3, 9), (4, 12))):
        return False
    sector_size = 1 << shift
    if len(data) % sector_size or len(data) < 2 * sector_size:
        return False
    sectors = len(data) // sector_size - 1
    fat_count, directory = _u32(data, 44), _u32(data, 48)
    mini_fat, mini_count = _u32(data, 60), _u32(data, 64)
    difat, difat_count = _u32(data, 68), _u32(data, 72)
    return (0 < fat_count <= sectors and directory < sectors
            and _u32(data, 56) == 4096 and mini_count <= sectors
            and (not mini_count or mini_fat < sectors)
            and difat_count <= sectors and (not difat_count or difat < sectors))


class LegacyOfficeBlobContentVerifier:
    """Host-selected, passive DOC/XLS adapter; the host provisions sandbox tools."""

    supported_extensions = frozenset(_MIME)

    def __init__(self, soffice_path: str, bwrap_path: str, prlimit_path: str,
                 scratch_root: str | Path, maximum_input_bytes: int = 32 * 1024 * 1024,
                 maximum_converted_bytes: int = 10 * 1024 * 1024,
                 concurrent_verifications: int = 2):
        paths = (soffice_path, bwrap_path, prlimit_path, str(scratch_root))
        if (any(not isinstance(path, str) or not os.path.isabs(path) for path in paths)
                or os.path.normpath(paths[3]) != paths[3]
                or type(maximum_input_bytes) is not int
                or not 1 <= maximum_input_bytes <= 100 * 1024 * 1024
                or type(maximum_converted_bytes) is not int
                or not 1 <= maximum_converted_bytes <= 10 * 1024 * 1024
                or type(concurrent_verifications) is not int
                or not 1 <= concurrent_verifications <= 32):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.soffice_path, self.bwrap_path, self.prlimit_path = paths[:3]
        self.scratch_root = Path(paths[3])
        self.maximum_input_bytes = maximum_input_bytes
        self.maximum_converted_bytes = maximum_converted_bytes
        self._permits = BoundedSemaphore(concurrent_verifications)
        self._package = OfficeBlobContentVerifier(
            maximum_input_bytes=maximum_converted_bytes,
            maximum_decoded_bytes=100 * 1024 * 1024,
            maximum_parts=10000, maximum_elements=2_000_000,
            concurrent_verifications=concurrent_verifications)

    def validate_ready(self) -> None:
        if sys.platform != "linux":
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        try:
            for executable in (self.soffice_path, self.bwrap_path, self.prlimit_path):
                if not Path(executable).is_file() or not os.access(executable, os.X_OK):
                    raise ValueError("missing converter")
            root = self.scratch_root.lstat()
            if (not stat.S_ISDIR(root.st_mode) or stat.S_IMODE(root.st_mode) != 0o700
                    or root.st_uid != os.geteuid()
                    or self.scratch_root.resolve() != self.scratch_root):
                raise ValueError("unsafe scratch root")
            self._package.validate_ready()
        except Exception:
            raise RuntimeError("BLOB_CAPABILITY_MISSING") from None

    def _convert(self, data: bytes, extension: str) -> bytes:
        try:
            with TemporaryDirectory(prefix="legacy-office-", dir=self.scratch_root) as name:
                job = Path(name)
                output, profile = job / "output", job / "profile"
                output.mkdir(mode=0o700)
                profile.mkdir(mode=0o700)
                source = job / ("source." + extension)
                descriptor = os.open(source, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "wb") as writer:
                    writer.write(data)
                args = [self.prlimit_path, "--cpu=20:20",
                        "--as=1073741824:1073741824", "--fsize=10485760:10485760",
                        "--", self.bwrap_path,
                        "--unshare-net", "--unshare-pid", "--die-with-parent",
                        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
                        "--ro-bind", "/lib64", "/lib64", "--symlink", "usr/bin", "/bin",
                        "--ro-bind", "/etc", "/etc", "--dev", "/dev", "--proc", "/proc",
                        "--dir", "/tmp", "--bind", name, name, "--clearenv",
                        "--setenv", "LC_ALL", "C", "--setenv", "PATH", "/usr/bin:/bin",
                        "--setenv", "HOME", name, "--setenv", "TMPDIR", name,
                        "--", self.soffice_path, "-env:UserInstallation=" + profile.as_uri(),
                        "--headless", "--nodefault", "--norestore", "--nolockcheck",
                        "--convert-to", extension + "x", "--outdir", str(output), str(source)]
                try:
                    process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL, cwd="/",
                                               env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                                               start_new_session=True)
                except OSError:
                    raise RuntimeError("BLOB_CAPABILITY_MISSING") from None
                try:
                    code = process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
                if code:
                    raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
                entries = list(output.iterdir())
                expected = output / ("source." + extension + "x")
                if len(entries) != 1 or entries[0] != expected:
                    raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
                info = expected.lstat()
                if (not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <=
                        self.maximum_converted_bytes):
                    raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
                converted = expected.read_bytes()
                if len(converted) != info.st_size:
                    raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
                return converted
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("BLOB_STORE_FAILED") from None

    def verify(self, stream, extension: str, maximum_bytes: int) -> BlobVerifiedContent:
        if extension not in _MIME:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        if type(maximum_bytes) is not int or maximum_bytes < 1:
            raise RuntimeError("BLOB_POLICY_INVALID")
        if not self._permits.acquire(blocking=False):
            raise RuntimeError("BLOB_VERIFICATION_BUSY")
        try:
            self.validate_ready()
            maximum = min(maximum_bytes, self.maximum_input_bytes)
            chunks, size = [], 0
            while True:
                try:
                    block = stream.read(65536)
                except Exception:
                    raise RuntimeError("BLOB_STORE_FAILED") from None
                if not isinstance(block, bytes):
                    raise RuntimeError("BLOB_STORE_FAILED")
                if not block:
                    break
                if len(block) > maximum - size:
                    raise RuntimeError("BLOB_SIZE_EXCEEDED")
                chunks.append(block)
                size += len(block)
            data = b"".join(chunks)
            if not _valid_container(data):
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            converted = self._convert(data, extension)
            try:
                self._package.verify(BytesIO(converted), extension + "x", len(converted))
            except Exception:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
            return BlobVerifiedContent(size, sha256(data).hexdigest(), _MIME[extension])
        finally:
            self._permits.release()
