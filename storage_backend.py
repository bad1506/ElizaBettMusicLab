from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    """Minimal contract for persistent user data.

    The current implementation deliberately remains filesystem-backed so local
    development and the existing API keep the same Path-based contract. A
    remote object-storage backend can implement this contract later without
    changing callers that only need a user root.
    """

    def user_root(self, user_id: str) -> Path: ...


class LocalStorageBackend:
    def __init__(self, base: Path):
        configured = os.getenv("SONA_DATA_DIR", "").strip()
        self.base = Path(configured).expanduser() if configured else base / "data"

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        return "".join(ch for ch in str(user_id) if ch.isalnum() or ch in "-_")[:80] or "local"

    def user_root(self, user_id: str) -> Path:
        root = self.base / "user_data" / self._safe_user_id(user_id)
        root.mkdir(parents=True, exist_ok=True)
        return root


def get_storage_backend(base: Path) -> StorageBackend:
    """Return the configured storage backend.

    Only ``local`` is enabled for now. Keeping the selection explicit prevents
    silently pretending that a remote bucket is durable when its credentials
    are not configured.
    """
    provider = os.getenv("SONA_STORAGE_PROVIDER", "local").strip().lower()
    if provider != "local":
        raise RuntimeError(
            f"Unsupported SONA_STORAGE_PROVIDER={provider!r}; use 'local' until a remote backend is configured."
        )
    return LocalStorageBackend(base)
