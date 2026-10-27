"""Optional bounded MP3/MP4 verifier backed by host-supplied FFmpeg binaries.

Input is passed over a pipe with only the pipe protocol enabled. The subprocess
never receives a client filename, URL, or shell command.
"""

from __future__ import annotations

from hashlib import sha256
from json import loads
from os import access, name as os_name, path, X_OK
from subprocess import DEVNULL, PIPE, run
from threading import BoundedSemaphore

from .upload_service import BlobVerifiedContent

if os_name == "posix":
    from resource import RLIMIT_AS, RLIMIT_CPU, setrlimit


_MIME = {"mp3": "audio/mpeg", "mp4": "video/mp4"}
_MP4_BRANDS = {b"isom", b"iso2", b"iso5", b"iso6", b"mp41", b"mp42",
               b"avc1", b"M4V ", b"M4V2", b"dash"}
_MPEG1_LAYER3_BITRATES = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128,
                          160, 192, 224, 256, 320, 0)
_MPEG2_LAYER3_BITRATES = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80,
                          96, 112, 128, 144, 160, 0)


def _complete_mp3(data: bytes, maximum_frames: int) -> bool:
    offset = 0
    if data.startswith(b"ID3"):
        if len(data) < 10 or data[3] not in (2, 3, 4) or data[4] == 0xff:
            return False
        if any(part & 0x80 for part in data[6:10]):
            return False
        tag_size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        footer = 10 if data[3] == 4 and data[5] & 0x10 else 0
        offset = 10 + tag_size + footer
        if offset > len(data):
            return False
    end = len(data) - (128 if len(data) >= 128 and data[-128:-125] == b"TAG" else 0)
    frames = 0
    first_rate = None
    while offset < end:
        if end - offset < 4 or frames >= maximum_frames:
            return False
        header = int.from_bytes(data[offset:offset + 4], "big")
        version = (header >> 19) & 3
        layer = (header >> 17) & 3
        bitrate_index = (header >> 12) & 15
        sample_index = (header >> 10) & 3
        padding = (header >> 9) & 1
        if (header >> 21 != 0x7ff or version == 1 or layer != 1
                or bitrate_index in (0, 15) or sample_index == 3):
            return False
        rate = (44100, 48000, 32000)[sample_index]
        rate //= 1 if version == 3 else 2 if version == 2 else 4
        if first_rate is None:
            first_rate = rate
        elif first_rate != rate:
            return False
        bitrates = _MPEG1_LAYER3_BITRATES if version == 3 else _MPEG2_LAYER3_BITRATES
        length = (144000 if version == 3 else 72000) * bitrates[bitrate_index] // rate + padding
        if length < 4 or length > end - offset:
            return False
        offset += length
        frames += 1
    return frames > 0 and offset == end


def _complete_mp4(data: bytes, maximum_boxes: int) -> bool:
    offset = 0
    count = 0
    kinds = set()
    while offset < len(data):
        if len(data) - offset < 8 or count >= maximum_boxes:
            return False
        size = int.from_bytes(data[offset:offset + 4], "big")
        kind = data[offset + 4:offset + 8]
        header = 8
        if size == 1:
            if len(data) - offset < 16:
                return False
            size = int.from_bytes(data[offset + 8:offset + 16], "big")
            header = 16
        elif size == 0:
            if kind != b"mdat":
                return False
            size = len(data) - offset
        if size < header or size > len(data) - offset:
            return False
        if count == 0:
            if kind != b"ftyp" or size < header + 8 or data[offset + header:offset + header + 4] not in _MP4_BRANDS:
                return False
        if kind in (b"ftyp", b"moov") and kind in kinds:
            return False
        kinds.add(kind)
        offset += size
        count += 1
    return {b"ftyp", b"moov", b"mdat"} <= kinds and offset == len(data)


class FfmpegBlobContentVerifier:
    """Passive Linux/POSIX adapter; full decode occurs only during verification."""

    supported_extensions = frozenset(_MIME)

    def __init__(self, ffprobe_path: str, ffmpeg_path: str,
                 maximum_input_bytes: int = 32 * 1024 * 1024,
                 maximum_frames: int = 100_000, maximum_video_pixels: int = 16_000_000,
                 concurrent_verifications: int = 2):
        if (not isinstance(ffprobe_path, str) or not path.isabs(ffprobe_path)
                or not isinstance(ffmpeg_path, str) or not path.isabs(ffmpeg_path)
                or type(maximum_input_bytes) is not int or not 1 <= maximum_input_bytes <= 100 * 1024 * 1024
                or type(maximum_frames) is not int or not 1 <= maximum_frames <= 1_000_000
                or type(maximum_video_pixels) is not int or not 1 <= maximum_video_pixels <= 64_000_000
                or type(concurrent_verifications) is not int
                or not 1 <= concurrent_verifications <= 32):
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.ffprobe_path = ffprobe_path
        self.ffmpeg_path = ffmpeg_path
        self.maximum_input_bytes = maximum_input_bytes
        self.maximum_frames = maximum_frames
        self.maximum_video_pixels = maximum_video_pixels
        self._permits = BoundedSemaphore(concurrent_verifications)

    @staticmethod
    def _limits() -> None:
        setrlimit(RLIMIT_CPU, (10, 10))
        setrlimit(RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))

    def validate_ready(self) -> None:
        if os_name != "posix":
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        for binary, prefix in ((self.ffprobe_path, b"ffprobe version "),
                               (self.ffmpeg_path, b"ffmpeg version ")):
            if not path.isfile(binary) or not access(binary, X_OK):
                raise RuntimeError("BLOB_CAPABILITY_MISSING")
            try:
                completed = run((binary, "-version"), stdout=PIPE, stderr=DEVNULL,
                                timeout=3, check=False, env={"LC_ALL": "C"})
            except Exception:
                raise RuntimeError("BLOB_CAPABILITY_MISSING") from None
            if completed.returncode != 0 or not completed.stdout.startswith(prefix):
                raise RuntimeError("BLOB_CAPABILITY_MISSING")

    def _run(self, binary: str, args: tuple[str, ...], data: bytes, output: bool):
        try:
            completed = run((binary, *args), input=data, stdout=PIPE if output else DEVNULL,
                            stderr=DEVNULL, timeout=15, check=False,
                            preexec_fn=self._limits, env={"LC_ALL": "C"})
        except Exception:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
        if completed.returncode != 0:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        return completed.stdout if output else b""

    def verify(self, stream, extension: str, maximum_bytes: int) -> BlobVerifiedContent:
        if extension not in _MIME:
            raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
        if type(maximum_bytes) is not int or maximum_bytes < 1:
            raise RuntimeError("BLOB_POLICY_INVALID")
        if not self._permits.acquire(blocking=False):
            raise RuntimeError("BLOB_VERIFICATION_BUSY")
        try:
            maximum = min(maximum_bytes, self.maximum_input_bytes)
            chunks = []
            digest = sha256()
            size = 0
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
                digest.update(block)
                size += len(block)
            data = b"".join(chunks)
            if extension == "mp3":
                valid = _complete_mp3(data, self.maximum_frames)
                demuxer = "mp3"
            else:
                valid = _complete_mp4(data, 1000)
                demuxer = "mov"
            if not valid:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            self.validate_ready()
            probe = self._run(self.ffprobe_path, (
                "-v", "error", "-protocol_whitelist", "pipe", "-f", demuxer,
                "-count_frames", "-show_entries",
                "stream=codec_type,codec_name,nb_read_frames,width,height,sample_rate:format=format_name",
                "-of", "json", "-i", "pipe:0"), data, True)
            if len(probe) > 65536:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED")
            try:
                result = loads(probe)
                streams = result["streams"]
                if not isinstance(streams, list) or not 1 <= len(streams) <= 8:
                    raise ValueError("invalid streams")
                if extension == "mp3":
                    if (result["format"]["format_name"] != "mp3" or len(streams) != 1
                            or streams[0]["codec_type"] != "audio"
                            or streams[0]["codec_name"] != "mp3"
                            or not 8000 <= int(streams[0]["sample_rate"]) <= 192000
                            or not 1 <= int(streams[0]["nb_read_frames"]) <= self.maximum_frames):
                        raise ValueError("invalid MP3")
                    maps = ("-map", "0:a:0")
                else:
                    videos = [item for item in streams if item["codec_type"] == "video"]
                    if ("mp4" not in result["format"]["format_name"]
                            or not 1 <= len(videos) <= 4
                            or any(item["codec_type"] not in ("video", "audio") for item in streams)
                            or any(not 1 <= int(item["width"]) * int(item["height"]) <= self.maximum_video_pixels
                                   or not 1 <= int(item["nb_read_frames"]) <= self.maximum_frames
                                   for item in videos)):
                        raise ValueError("invalid MP4")
                    maps = ("-map", "0:v", "-map", "0:a?")
            except Exception:
                raise RuntimeError("BLOB_FORMAT_NOT_ALLOWED") from None
            self._run(self.ffmpeg_path, (
                "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode",
                "-threads", "1", "-protocol_whitelist", "pipe", "-f", demuxer,
                "-i", "pipe:0", *maps, "-f", "null", "-"), data, False)
            return BlobVerifiedContent(size, digest.hexdigest(), _MIME[extension])
        finally:
            self._permits.release()
