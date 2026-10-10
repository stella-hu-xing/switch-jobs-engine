"""Shared id / hashing / time helpers."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def slugify(value: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:max_length] or "item"


def stable_hash(*parts: str) -> str:
    """Deterministic short hash used for job dedup keys."""
    normalized = "|".join(normalize_text(p) for p in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def normalize_text(value: str | None) -> str:
    """Lowercase, collapse whitespace, drop punctuation - for comparisons."""
    if not value:
        return ""
    lowered = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", lowered).strip()


def token_set(value: str | None) -> set[str]:
    return set(normalize_text(value).split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
