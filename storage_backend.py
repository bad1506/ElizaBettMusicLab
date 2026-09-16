from __future__ import annotations

import json
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

_META_DIR = ".sona_storage_meta"
_LOCK_NAME = ".sona-storage.lock"
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()
_BACKENDS: dict[tuple[str, str], "StorageBackend"] = {}
_BACKENDS_LOCK = threading.Lock()


@dataclass(frozen=True)
class HydrateResult:
    downloaded: int = 0
    skipped: int = 0
    preserved_local: int = 0


@dataclass(frozen=True)
class SyncResult:
    uploaded: int = 0
    skipped: int = 0


class StorageBackend(Protocol):
    """Path-compatible persistent storage contract for a user workspace."""

    def user_root(self, user_id: str) -> Path: ...

    def hydrate(self, user_id: str, *, prefixes: list[str] | None = None) -> HydrateResult: ...

    def sync_file(self, user_id: str, path: Path, *, key: str | None = None) -> SyncResult: ...

    def sync_tree(self, user_id: str, root: Path, *, prefix: str | None = None) -> SyncResult: ...

    def delete_files(self, user_id: str, paths: list[Path]) -> int: ...


class _WorkspaceLock:
    def __init__(self, root: Path):
        self.root = root
        self._thread_lock: threading.Lock | None = None
        self._handle = None

    def __enter__(self):
        lock_key = str(self.root.resolve())
        with _THREAD_LOCKS_GUARD:
            self._thread_lock = _THREAD_LOCKS.setdefault(lock_key, threading.Lock())
        self._thread_lock.acquire()
        try:
            try:
                import fcntl
            except ImportError:
                fcntl = None
            if fcntl is not None:
                self._handle = (self.root / _LOCK_NAME).open("a+", encoding="utf-8")
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        except Exception:
            self._thread_lock.release()
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._handle is not None:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
                self._handle.close()
        finally:
            if self._thread_lock:
                self._thread_lock.release()


def _safe_user_id(user_id: str) -> str:
    return "".join(ch for ch in str(user_id) if ch.isalnum() or ch in "-_")[:80] or "local"


def _safe_relative(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("Storage path escapes the user workspace")
    return resolved_path.relative_to(resolved_root)


def _is_syncable(path: Path) -> bool:
    return path.is_file() and path.name != _LOCK_NAME and _META_DIR not in path.parts


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.sona-tmp-{os.getpid()}-{threading.get_ident()}")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_remote_time(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _retryable(exc: Exception) -> bool:
    try:
        from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError
        if isinstance(exc, ClientError):
            status = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
            return status >= 500 or status in {408, 429}
        return isinstance(exc, (EndpointConnectionError, ReadTimeoutError, TimeoutError, ConnectionError))
    except ImportError:
        return isinstance(exc, (TimeoutError, ConnectionError))


class LocalStorageBackend:
    def __init__(self, base: Path):
        configured = os.getenv("SONA_DATA_DIR", "").strip()
        self.base = Path(configured).expanduser() if configured else base / "data"

    def user_root(self, user_id: str) -> Path:
        root = self.base / "user_data" / _safe_user_id(user_id)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def hydrate(self, user_id: str, *, prefixes: list[str] | None = None) -> HydrateResult:
        return HydrateResult()

    def sync_file(self, user_id: str, path: Path, *, key: str | None = None) -> SyncResult:
        return SyncResult(uploaded=int(path.is_file()))

    def sync_tree(self, user_id: str, root: Path, *, prefix: str | None = None) -> SyncResult:
        return SyncResult(uploaded=sum(1 for p in root.rglob("*") if _is_syncable(p)))

    def delete_files(self, user_id: str, paths: list[Path]) -> int:
        return 0


class S3StorageBackend(LocalStorageBackend):
    """S3/R2-compatible durable storage backed by a local Path workspace."""

    def __init__(self, base: Path):
        super().__init__(base)
        self.endpoint = os.getenv("SONA_S3_ENDPOINT", "").strip() or None
        self.bucket = os.getenv("SONA_S3_BUCKET", "").strip()
        self.region = os.getenv("SONA_S3_REGION", "us-east-1").strip() or "us-east-1"
        self.access_key = os.getenv("SONA_S3_ACCESS_KEY_ID", "").strip()
        self.secret_key = os.getenv("SONA_S3_SECRET_ACCESS_KEY", "").strip()
        self.prefix = os.getenv("SONA_S3_PREFIX", "sona").strip("/")
        self.max_attempts = max(1, min(int(os.getenv("SONA_S3_MAX_ATTEMPTS", "4")), 5))
        self.hydrate_ttl = max(0, int(os.getenv("SONA_S3_HYDRATE_TTL", "30")))
        self._hydrated: dict[str, float] = {}
        self._hydrated_lock = threading.Lock()
        if not self.bucket:
            raise RuntimeError("SONA_S3_BUCKET is required when S3 storage is enabled")
        if not self.access_key or not self.secret_key:
            raise RuntimeError("S3 credentials are required when S3 storage is enabled")

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required when S3 storage is enabled") from exc
        return boto3.client("s3", endpoint_url=self.endpoint, region_name=self.region, aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key)

    def _call(self, operation, *args, **kwargs):
        delay = 0.25
        for attempt in range(self.max_attempts):
            try:
                return operation(*args, **kwargs)
            except Exception as exc:
                if attempt + 1 >= self.max_attempts or not _retryable(exc):
                    raise
                time.sleep(delay + random.uniform(0, delay * 0.25))
                delay = min(delay * 2, 2.0)

    def _key(self, user_id: str, relative: Path) -> str:
        relative_text = relative.as_posix().lstrip("/")
        parts = (self.prefix, "user_data", _safe_user_id(user_id), relative_text)
        return "/".join(part for part in parts if part and part != ".")

    def _meta_path(self, root: Path, relative: Path) -> Path:
        return root / _META_DIR / (relative.as_posix() + ".json")

    def _read_meta(self, root: Path, relative: Path) -> dict:
        try:
            return json.loads(self._meta_path(root, relative).read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    def _write_meta(self, root: Path, relative: Path, metadata: dict) -> None:
        _atomic_write(self._meta_path(root, relative), json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode("utf-8"))

    def _base_prefix(self, user_id: str) -> str:
        return self._key(user_id, Path(""))

    def hydrate(self, user_id: str, *, prefixes: list[str] | None = None) -> HydrateResult:
        root = self.user_root(user_id)
        now = time.monotonic()
        with self._hydrated_lock:
            if self.hydrate_ttl and now - self._hydrated.get(_safe_user_id(user_id), 0) < self.hydrate_ttl:
                return HydrateResult()
        client = self._client()
        base_prefix = self._base_prefix(user_id).rstrip("/") + "/"
        requested = [p.strip("/") for p in (prefixes or []) if p.strip("/")]
        downloaded = skipped = preserved = 0
        with _WorkspaceLock(root):
            paginator = client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=base_prefix)
            for page in pages:
                for obj in page.get("Contents", []):
                    key = str(obj.get("Key", ""))
                    if not key.startswith(base_prefix) or key.endswith("/"):
                        continue
                    relative_text = key[len(base_prefix):]
                    if requested and not any(relative_text == p or relative_text.startswith(p + "/") for p in requested):
                        continue
                    relative = Path(relative_text)
                    target = (root / relative).resolve()
                    if not target.is_relative_to(root.resolve()):
                        continue
                    remote_etag = str(obj.get("ETag", "")).strip('"')
                    remote_size = obj.get("Size")
                    remote_modified = obj.get("LastModified")
                    remote_ts = remote_modified.timestamp() if hasattr(remote_modified, "timestamp") else 0.0
                    if target.exists():
                        meta = self._read_meta(root, relative)
                        if meta.get("etag") == remote_etag and meta.get("size") == remote_size:
                            skipped += 1
                            continue
                        synced_at = _parse_remote_time(str(meta.get("synced_at", "")))
                        if synced_at and target.stat().st_mtime > synced_at + 1.0:
                            preserved += 1
                            continue
                    response = self._call(client.get_object, Bucket=self.bucket, Key=key)
                    _atomic_write(target, response["Body"].read())
                    if remote_ts:
                        try:
                            os.utime(target, (remote_ts, remote_ts))
                        except OSError:
                            pass
                    self._write_meta(root, relative, {"etag": remote_etag, "size": remote_size, "last_modified": str(remote_modified or ""), "synced_at": _utc_now().isoformat()})
                    downloaded += 1
            with self._hydrated_lock:
                self._hydrated[_safe_user_id(user_id)] = time.monotonic()
        return HydrateResult(downloaded=downloaded, skipped=skipped, preserved_local=preserved)

    def sync_file(self, user_id: str, path: Path, *, key: str | None = None) -> SyncResult:
        root = self.user_root(user_id)
        relative = _safe_relative(root, path)
        if not _is_syncable(path):
            return SyncResult()
        object_key = key or self._key(user_id, relative)
        with _WorkspaceLock(root):
            client = self._client()
            self._call(client.put_object, Bucket=self.bucket, Key=object_key, Body=path.read_bytes())
            try:
                head = self._call(client.head_object, Bucket=self.bucket, Key=object_key)
                etag = str(head.get("ETag", "")).strip('"')
                size = head.get("ContentLength", path.stat().st_size)
                modified = head.get("LastModified")
            except Exception:
                etag = ""
                size = path.stat().st_size
                modified = None
            self._write_meta(root, relative, {"etag": etag, "size": size, "last_modified": str(modified or ""), "synced_at": _utc_now().isoformat()})
        return SyncResult(uploaded=1)

    def delete_files(self, user_id: str, paths: list[Path]) -> int:
        root = self.user_root(user_id)
        relatives: list[Path] = []
        for path in paths:
            relative = _safe_relative(root, path)
            if relative not in relatives:
                relatives.append(relative)
        if not relatives:
            return 0
        deleted = 0
        with _WorkspaceLock(root):
            client = self._client()
            for offset in range(0, len(relatives), 1000):
                batch = relatives[offset:offset + 1000]
                response = self._call(client.delete_objects, Bucket=self.bucket, Delete={"Objects": [{"Key": self._key(user_id, relative)} for relative in batch], "Quiet": True})
                errors = response.get("Errors", []) if isinstance(response, dict) else []
                if errors:
                    raise RuntimeError("Remote storage deletion failed")
                deleted += len(batch)
                for relative in batch:
                    self._meta_path(root, relative).unlink(missing_ok=True)
        return deleted

    def sync_tree(self, user_id: str, root: Path, *, prefix: str | None = None) -> SyncResult:
        workspace = self.user_root(user_id)
        root_resolved = root.resolve()
        if not root_resolved.is_relative_to(workspace.resolve()):
            raise ValueError("Sync root must be inside the user workspace")
        prefix_norm = prefix.strip("/") if prefix else ""
        paths = [p for p in sorted(root_resolved.rglob("*")) if _is_syncable(p)]
        uploaded = 0
        for path in paths:
            relative = _safe_relative(workspace, path).as_posix()
            if prefix_norm and not (relative == prefix_norm or relative.startswith(prefix_norm + "/")):
                continue
            self.sync_file(user_id, path)
            uploaded += 1
        return SyncResult(uploaded=uploaded)


def get_storage_backend(base: Path) -> StorageBackend:
    provider = os.getenv("SONA_STORAGE_PROVIDER", "local").strip().lower()
    key = (str(base.resolve()), provider)
    with _BACKENDS_LOCK:
        cached = _BACKENDS.get(key)
        if cached is not None:
            return cached
        if provider == "local":
            backend: StorageBackend = LocalStorageBackend(base)
        elif provider in {"s3", "r2"}:
            backend = S3StorageBackend(base)
        else:
            raise RuntimeError(f"Unsupported SONA_STORAGE_PROVIDER={provider!r}")
        _BACKENDS[key] = backend
        return backend
