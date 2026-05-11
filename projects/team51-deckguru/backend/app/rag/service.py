"""RAG Service interface and runtime factory."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from app.schemas.shared import IndexName, RagChunk
from app.settings import settings


class RagUnavailableError(RuntimeError):
    """RAG backend is unavailable or cannot serve the requested collection."""


class RagService(Protocol):
    def search(
        self,
        index: IndexName,
        query: str,
        *,
        k: int,
        patch_version: str,
        where: dict | None = None,
    ) -> list[RagChunk]: ...

    def multi_search(
        self,
        plan: list[tuple[IndexName, str, int]],
        *,
        patch_version: str,
    ) -> list[RagChunk]: ...

    def get_whitelist(self, patch_version: str) -> dict[str, set[str]]:
        """Return names allowed by the current patch RAG whitelist."""
        ...


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    """Return the runtime RAG service.

    The default path is Chroma-backed. Tests and explicit demo paths should
    inject their own RagService instead of depending on import-time globals.
    """
    from app.rag.chroma_service import ChromaRagService

    return ChromaRagService(
        persist_path=settings.chroma_path,
        min_score=settings.rag_min_score,
    )


def clear_rag_service_cache() -> None:
    """Refresh hook for tests and local rebuild scripts."""
    get_rag_service.cache_clear()


__all__ = [
    "RagService",
    "RagUnavailableError",
    "get_rag_service",
    "clear_rag_service_cache",
]
