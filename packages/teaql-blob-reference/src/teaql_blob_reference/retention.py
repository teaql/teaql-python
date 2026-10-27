"""Validated, immutable host policy and time rules for Blob retention."""

from dataclasses import dataclass


MAX_RETENTION_EPOCH_MS = 8_640_000_000_000_000


def valid_time(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_RETENTION_EPOCH_MS


def valid_seconds(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_RETENTION_EPOCH_MS // 1000


def retention_deadline(base_ms: int, seconds: int) -> int:
    if not valid_time(base_ms):
        raise RuntimeError("BLOB_REFERENCE_INVALID")
    if not valid_seconds(seconds) or seconds > (MAX_RETENTION_EPOCH_MS - base_ms) // 1000:
        raise RuntimeError("BLOB_POLICY_INVALID")
    return base_ms + seconds * 1000


def effective_retention(accepted: tuple[int, ...], proposed: int) -> int:
    if not valid_seconds(proposed) or any(not valid_seconds(value) for value in accepted):
        raise RuntimeError("BLOB_POLICY_INVALID")
    return max((proposed, *accepted))


def unreferenced_eligible_at(last_unbound_ms: int, seconds: int,
                             floor_until_ms: int | None) -> int:
    deadline = retention_deadline(last_unbound_ms, seconds)
    if floor_until_ms is not None:
        if not valid_time(floor_until_ms):
            raise RuntimeError("BLOB_REFERENCE_INVALID")
        deadline = max(deadline, floor_until_ms)
    return deadline


def require_bindable(status: str, now_ms: int, completed_ms: int | None,
                     unbound_seconds: int, unreferenced_eligible_ms: int | None) -> None:
    if not valid_time(now_ms):
        raise RuntimeError("BLOB_REFERENCE_INVALID")
    if status == "initiated":
        raise RuntimeError("BLOB_UPLOAD_INCOMPLETE")
    if status in ("deleting", "deleted"):
        raise RuntimeError("BLOB_REFERENCE_EXPIRED")
    if status == "uploaded_unbound":
        if completed_ms is None:
            raise RuntimeError("BLOB_REFERENCE_INVALID")
        if now_ms >= retention_deadline(completed_ms, unbound_seconds):
            raise RuntimeError("BLOB_REFERENCE_EXPIRED")
    elif status == "available":
        if unreferenced_eligible_ms is not None:
            if not valid_time(unreferenced_eligible_ms):
                raise RuntimeError("BLOB_REFERENCE_INVALID")
            if now_ms >= unreferenced_eligible_ms:
                raise RuntimeError("BLOB_REFERENCE_EXPIRED")
    else:
        raise RuntimeError("BLOB_REFERENCE_INVALID")


@dataclass(frozen=True)
class BlobRetentionPolicy:
    profile: str
    upload_mode: str
    unbound_retention_seconds: int
    unreferenced_retention_seconds: int
    minimum_retention_seconds: int

    def __post_init__(self):
        from .sqlite_catalog import _scope
        if (not _scope(self.profile) or self.upload_mode not in ("server_stream", "direct")
                or not all(valid_seconds(value) for value in (
                    self.unbound_retention_seconds, self.unreferenced_retention_seconds,
                    self.minimum_retention_seconds))):
            raise RuntimeError("BLOB_POLICY_INVALID")
