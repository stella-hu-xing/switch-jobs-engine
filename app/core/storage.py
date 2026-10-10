"""Storage abstraction.

Business logic only ever depends on the ``StorageBackend`` protocol, so the
persistence layer can later move to Firestore/Postgres without touching modules.

Two implementations ship today:
  * ``LocalJSONStorage`` -- JSON documents under ``./data`` (default, dev)
  * ``GCSStorage``       -- same JSON documents in a GCS bucket (Cloud Run)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.core.settings import Settings, get_settings

JsonDoc = dict[str, Any]


@runtime_checkable
class StorageBackend(Protocol):
    """Document store keyed by ``(collection, doc_id)``."""

    def put(self, collection: str, doc_id: str, document: JsonDoc) -> None: ...

    def get(self, collection: str, doc_id: str) -> JsonDoc | None: ...

    def list(self, collection: str) -> list[JsonDoc]: ...

    def delete(self, collection: str, doc_id: str) -> bool: ...

    def exists(self, collection: str, doc_id: str) -> bool: ...


def _safe_name(name: str) -> str:
    """Make an id safe to use as a path segment."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_.") else "-" for ch in name)
    return cleaned.strip("-.") or "unnamed"


class LocalJSONStorage:
    """Filesystem backend: ``<root>/<collection>/<doc_id>.json``."""

    def __init__(self, root: str | Path = "./data") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, collection: str, doc_id: str) -> Path:
        return self.root / _safe_name(collection) / f"{_safe_name(doc_id)}.json"

    def put(self, collection: str, doc_id: str, document: JsonDoc) -> None:
        path = self._path(collection, doc_id)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document, indent=2, default=str), encoding="utf-8")

    def get(self, collection: str, doc_id: str) -> JsonDoc | None:
        path = self._path(collection, doc_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, collection: str) -> list[JsonDoc]:
        folder = self.root / _safe_name(collection)
        if not folder.exists():
            return []
        docs: list[JsonDoc] = []
        for path in sorted(folder.glob("*.json")):
            try:
                docs.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:  # pragma: no cover - corrupt file guard
                continue
        return docs

    def delete(self, collection: str, doc_id: str) -> bool:
        path = self._path(collection, doc_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, collection: str, doc_id: str) -> bool:
        return self._path(collection, doc_id).exists()


class GCSStorage:
    """Google Cloud Storage backend: ``gs://<bucket>/<prefix>/<collection>/<id>.json``."""

    def __init__(self, bucket: str, prefix: str = "switch-jobs-engine") -> None:
        if not bucket:
            raise ValueError("GCS_BUCKET must be set when STORAGE_BACKEND=gcs")
        from google.cloud import storage as gcs  # lazy: optional dependency at dev time

        self._client = gcs.Client()
        self._bucket = self._client.bucket(bucket)
        self._prefix = prefix.strip("/")

    def _blob_name(self, collection: str, doc_id: str) -> str:
        return f"{self._prefix}/{_safe_name(collection)}/{_safe_name(doc_id)}.json"

    def put(self, collection: str, doc_id: str, document: JsonDoc) -> None:
        blob = self._bucket.blob(self._blob_name(collection, doc_id))
        blob.upload_from_string(
            json.dumps(document, indent=2, default=str),
            content_type="application/json",
        )

    def get(self, collection: str, doc_id: str) -> JsonDoc | None:
        blob = self._bucket.blob(self._blob_name(collection, doc_id))
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())

    def list(self, collection: str) -> list[JsonDoc]:
        prefix = f"{self._prefix}/{_safe_name(collection)}/"
        docs: list[JsonDoc] = []
        for blob in self._client.list_blobs(self._bucket, prefix=prefix):
            if not blob.name.endswith(".json"):
                continue
            try:
                docs.append(json.loads(blob.download_as_text()))
            except json.JSONDecodeError:  # pragma: no cover
                continue
        return docs

    def delete(self, collection: str, doc_id: str) -> bool:
        blob = self._bucket.blob(self._blob_name(collection, doc_id))
        if not blob.exists():
            return False
        blob.delete()
        return True

    def exists(self, collection: str, doc_id: str) -> bool:
        return self._bucket.blob(self._blob_name(collection, doc_id)).exists()


class InMemoryStorage:
    """Test double, also handy for ephemeral runs."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, JsonDoc]] = {}

    def put(self, collection: str, doc_id: str, document: JsonDoc) -> None:
        self._data.setdefault(collection, {})[doc_id] = json.loads(
            json.dumps(document, default=str)
        )

    def get(self, collection: str, doc_id: str) -> JsonDoc | None:
        return self._data.get(collection, {}).get(doc_id)

    def list(self, collection: str) -> list[JsonDoc]:
        return list(self._data.get(collection, {}).values())

    def delete(self, collection: str, doc_id: str) -> bool:
        return self._data.get(collection, {}).pop(doc_id, None) is not None

    def exists(self, collection: str, doc_id: str) -> bool:
        return doc_id in self._data.get(collection, {})


_backend: StorageBackend | None = None


def build_storage(settings: Settings | None = None) -> StorageBackend:
    settings = settings or get_settings()
    if settings.storage_backend == "gcs":
        return GCSStorage(settings.gcs_bucket, settings.gcs_prefix)
    return LocalJSONStorage(settings.local_storage_dir)


def get_storage() -> StorageBackend:
    """FastAPI dependency returning the process-wide storage backend."""
    global _backend
    if _backend is None:
        _backend = build_storage()
    return _backend


def set_storage(backend: StorageBackend | None) -> None:
    """Override the backend (used by tests)."""
    global _backend
    _backend = backend


class Collections:
    """Collection names used across modules."""

    PROFILES = "profiles"
    JOBS = "jobs"
    COMPANIES = "companies"
    MATCHES = "matches"
    APPLICATIONS = "applications"
    INTERVIEWS = "interviews"
    DEBRIEFS = "debriefs"
    RUNS = "runs"
