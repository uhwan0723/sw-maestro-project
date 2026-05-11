"""Chroma-backed implementation of the backend RagService contract."""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import structlog

from app.observability import elapsed_ms, preview
from app.rag.filters import merge_where, patch_where
from app.rag.service import RagUnavailableError
from app.schemas.shared import IndexName, RagChunk
from app.settings import settings

logger = structlog.get_logger()

BACKEND_ROOT = Path(__file__).resolve().parents[2]

RAG_INDICES: tuple[IndexName, ...] = (
    "units",
    "traits",
    "items",
    "augments",
    "deck_templates",
    "playbook",
    "patch_summary",
    "glossary",
)
WHITELIST_INDICES: tuple[IndexName, ...] = ("units", "items", "traits", "augments")


class BGEM3Embedding:
    """Lazy BGE-M3 sentence-transformers embedder."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        *,
        use_fp16: bool = False,
        batch_size: int = 12,
        max_length: int = 8192,
    ) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.max_length = max_length
        self._model: Any | None = None

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        output = self._load_model().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in output]

    def _load_model(self) -> Any:
        if self._model is None:
            started = time.perf_counter()
            logger.info(
                "embedding_model_load_start",
                stage="rag",
                model=self.model_name,
            )
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RagUnavailableError(
                    "sentence-transformers is not installed. Install backend RAG dependencies with "
                    '`pip install -e ".[backend,dev,rag]"`.'
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name)
                self._model.max_seq_length = self.max_length
            except Exception as exc:
                raise RagUnavailableError(
                    f"failed to load embedding model {self.model_name}. "
                    "Ensure the model exists in the local cache or network access is available."
                ) from exc
            logger.info(
                "embedding_model_load_done",
                stage="rag",
                model=self.model_name,
                latency_ms=elapsed_ms(started),
            )
        return self._model


class ChromaRagService:
    def __init__(
        self,
        *,
        persist_path: Path,
        min_score: float = 0.2,
        client: Any | None = None,
        embedder: Any | None = None,
        whitelist_ttl_s: int = 300,
        whitelist_max_size: int = 16,
    ) -> None:
        self.persist_path = resolve_chroma_path(persist_path)
        self.min_score = min_score
        self.client = client or _create_client(self.persist_path)
        self.embedder = embedder or BGEM3Embedding(settings.embedding_model)
        self.whitelist_ttl_s = whitelist_ttl_s
        self.whitelist_max_size = whitelist_max_size
        self._whitelist_cache: OrderedDict[str, tuple[float, dict[str, set[str]]]] = OrderedDict()

    def search(
        self,
        index: IndexName,
        query: str,
        *,
        k: int,
        patch_version: str,
        where: dict | None = None,
    ) -> list[RagChunk]:
        started = time.perf_counter()
        logger.info(
            "rag_search_start",
            stage="rag",
            index=index,
            k=k,
            patch_version=patch_version,
            query=preview(query, limit=64),
        )
        try:
            collection = self._get_collection(index, missing_is_empty=False)
            result = collection.query(
                query_embeddings=[self.embedder.embed(query)],
                n_results=max(k * 5, k),
                where=merge_where(where, patch_where(patch_version)),
                include=["documents", "metadatas", "distances"],
            )
        except RagUnavailableError as exc:
            logger.warning(
                "rag_search_unavailable",
                stage="rag",
                index=index,
                latency_ms=elapsed_ms(started),
                error=str(exc),
            )
            raise
        except Exception as exc:
            logger.warning(
                "rag_search_failed",
                stage="rag",
                index=index,
                latency_ms=elapsed_ms(started),
                error=str(exc),
            )
            raise RagUnavailableError(f"failed to query RAG collection {index}") from exc

        chunks = self._format_query_result(index, result, k)
        logger.info(
            "rag_search_done",
            stage="rag",
            index=index,
            hits=len(chunks),
            top_score=round(chunks[0].score, 3) if chunks else 0.0,
            latency_ms=elapsed_ms(started),
        )
        return chunks

    def multi_search(
        self,
        plan: list[tuple[IndexName, str, int]],
        *,
        patch_version: str,
    ) -> list[RagChunk]:
        started = time.perf_counter()
        logger.info(
            "rag_multi_search_start",
            stage="rag",
            collections=[index for index, _, _ in plan],
            patch_version=patch_version,
        )
        deduped: dict[str, RagChunk] = {}
        succeeded = False
        errors: list[str] = []
        for index, query, k in plan:
            try:
                chunks = self.search(index, query, k=k, patch_version=patch_version)
            except RagUnavailableError as exc:
                errors.append(f"{index}: {exc}")
                continue

            succeeded = True
            for chunk in chunks:
                current = deduped.get(chunk.id)
                if current is None or chunk.score > current.score:
                    deduped[chunk.id] = chunk
        if not succeeded and errors:
            logger.warning(
                "rag_multi_search_failed",
                stage="rag",
                errors=errors,
                latency_ms=elapsed_ms(started),
            )
            raise RagUnavailableError(
                "all planned RAG collections are unavailable: " + "; ".join(errors)
            )
        chunks = sorted(deduped.values(), key=lambda chunk: chunk.score, reverse=True)
        logger.info(
            "rag_multi_search_done",
            stage="rag",
            chunks=len(chunks),
            errors=len(errors),
            latency_ms=elapsed_ms(started),
        )
        return chunks

    def get_whitelist(self, patch_version: str) -> dict[str, set[str]]:
        started = time.perf_counter()
        now = time.time()
        cached = self._whitelist_cache.get(patch_version)
        if cached and now - cached[0] < self.whitelist_ttl_s:
            self._whitelist_cache.move_to_end(patch_version)
            whitelist = {key: set(values) for key, values in cached[1].items()}
            logger.info(
                "rag_whitelist_cache_hit",
                stage="rag",
                patch_version=patch_version,
                counts={key: len(values) for key, values in whitelist.items()},
                latency_ms=elapsed_ms(started),
            )
            return whitelist

        logger.info("rag_whitelist_load_start", stage="rag", patch_version=patch_version)
        whitelist: dict[str, set[str]] = {}
        where = patch_where(patch_version)
        for index in WHITELIST_INDICES:
            collection = self._get_collection(index, missing_is_empty=True)
            if collection is None:
                whitelist[index] = set()
                continue
            try:
                result = collection.get(where=where, include=["metadatas"])
            except Exception:
                whitelist[index] = set()
                continue
            whitelist[index] = {
                str(metadata["name"])
                for metadata in result.get("metadatas", [])
                if metadata and metadata.get("name")
            }

        self._whitelist_cache[patch_version] = (now, whitelist)
        self._whitelist_cache.move_to_end(patch_version)
        while len(self._whitelist_cache) > self.whitelist_max_size:
            self._whitelist_cache.popitem(last=False)
        result = {key: set(values) for key, values in whitelist.items()}
        logger.info(
            "rag_whitelist_load_done",
            stage="rag",
            patch_version=patch_version,
            counts={key: len(values) for key, values in result.items()},
            latency_ms=elapsed_ms(started),
        )
        return result

    def _get_collection(self, index: IndexName, *, missing_is_empty: bool) -> Any | None:
        try:
            return self.client.get_collection(name=index)
        except Exception as exc:
            if missing_is_empty:
                return None
            raise RagUnavailableError(f"RAG collection {index} is not available") from exc

    def _format_query_result(self, index: IndexName, result: dict[str, Any], k: int) -> list[RagChunk]:
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        deduped: dict[str, RagChunk] = {}
        for item_id, document, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=False
        ):
            score = _distance_to_score(float(distance))
            if score < self.min_score:
                continue
            chunk = RagChunk(
                id=str(item_id),
                index=index,
                text=str(document),
                metadata=_decode_metadata(metadata or {}),
                score=score,
            )
            current = deduped.get(chunk.id)
            if current is None or chunk.score > current.score:
                deduped[chunk.id] = chunk
        return sorted(deduped.values(), key=lambda chunk: chunk.score, reverse=True)[:k]


def count_chroma_collections(persist_path: Path) -> dict[str, int]:
    counts = {index: 0 for index in RAG_INDICES}
    resolved_path = resolve_chroma_path(persist_path)
    if not resolved_path.exists():
        return counts
    try:
        client = _create_client(resolved_path)
    except RagUnavailableError:
        return counts

    for index in RAG_INDICES:
        try:
            counts[index] = int(client.get_collection(name=index).count())
        except Exception:
            counts[index] = 0
    return counts


def _distance_to_score(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


def resolve_chroma_path(path: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


def _decode_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and value[:1] in {"[", "{"}:
            try:
                decoded[key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        decoded[key] = value
    return decoded


def _create_client(persist_path: Path) -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RagUnavailableError(
            "chromadb is not installed. Install backend RAG dependencies with "
            '`pip install -e ".[backend,dev,rag]"`.'
        ) from exc
    try:
        return chromadb.PersistentClient(path=str(resolve_chroma_path(persist_path)))
    except Exception as exc:
        raise RagUnavailableError(f"failed to open Chroma path {persist_path}") from exc


__all__ = [
    "BGEM3Embedding",
    "ChromaRagService",
    "RAG_INDICES",
    "WHITELIST_INDICES",
    "count_chroma_collections",
    "resolve_chroma_path",
]
