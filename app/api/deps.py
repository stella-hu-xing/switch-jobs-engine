"""FastAPI dependency providers shared across routers."""

from __future__ import annotations

from app.core.llm_client import LLMClient, get_llm_client
from app.core.storage import StorageBackend, get_storage


def storage_dep() -> StorageBackend:
    return get_storage()


def llm_dep() -> LLMClient:
    return get_llm_client()
