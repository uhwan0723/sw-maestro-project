import json
import re
from pathlib import Path
from typing import Any

from deckguru_rag.embeddings import BGEM3Embedding


TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣_.%]+")
PATCH_FAMILY_RE = re.compile(r"^\d+\.\d+$")


class ChromaPatchSummarySearch:
    def __init__(self, *, data_dir: Path, persist_dir: Path) -> None:
        chromadb = _import_chromadb()
        self.data_dir = data_dir
        self.embedder = BGEM3Embedding()
        self.client = chromadb.PersistentClient(path=str(persist_dir))

    def get_current_patch(self, index: str = "patch_summary") -> str:
        manifest_dir = self.data_dir if index == "patch_summary" else self.data_dir.parent / index
        manifest = json.loads((manifest_dir / "current_patch.json").read_text(encoding="utf-8"))
        return str(manifest["current_patch"])

    def search(
        self,
        query: str,
        *,
        index: str = "patch_summary",
        k: int = 5,
        patch_version: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if patch_version is None:
            patch_version = _patch_family_base(self.get_current_patch(index))
        collection = self.client.get_or_create_collection(name=index)
        chroma_where = _patch_where(
            patch_version=patch_version,
            available_versions=self._available_patch_versions(index),
        )
        if where:
            chroma_where.update(where)

        result = collection.query(
            query_embeddings=[self.embedder.embed(query)],
            n_results=max(k * 5, k),
            where=chroma_where,
            include=["documents", "metadatas", "distances"],
        )
        return _rerank(_format_results(result), query)[:k]

    def _available_patch_versions(self, index: str) -> list[str]:
        index_dir = self.data_dir if index == "patch_summary" else self.data_dir.parent / index
        versions = {path.stem for path in index_dir.glob("*.jsonl")}
        for path in index_dir.glob("*.jsonl"):
            for record in _load_jsonl(path):
                patch_version = record.get("patch_version")
                if isinstance(patch_version, str) and patch_version:
                    versions.add(patch_version)
        return sorted(versions)


def _patch_where(*, patch_version: str, available_versions: list[str]) -> dict[str, Any]:
    if not PATCH_FAMILY_RE.match(patch_version):
        return {"patch_version": patch_version}

    family_re = re.compile(rf"^{re.escape(patch_version)}[a-z]?$", flags=re.IGNORECASE)
    family_versions = [version for version in available_versions if family_re.match(version)]
    if not family_versions:
        family_versions = [patch_version]
    return {"patch_version": {"$in": family_versions}}


def _patch_family_base(patch_version: str) -> str:
    match = re.match(r"^(\d+\.\d+)[a-z]$", patch_version, flags=re.IGNORECASE)
    return match.group(1) if match else patch_version


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _format_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    formatted: list[dict[str, Any]] = []
    for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
        score = 1.0 / (1.0 + float(distance))
        formatted.append(
            {
                "id": item_id,
                "text": document,
                "score": round(score, 4),
                **metadata,
            }
        )
    return formatted


def _rerank(results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_tokens = set(_tokens(query))
    reranked: list[dict[str, Any]] = []
    for result in results:
        searchable = " ".join(
            str(result.get(field) or "")
            for field in ("target_name", "target_kind", "change_type", "text")
        )
        result_tokens = set(_tokens(searchable))
        overlap = len(query_tokens & result_tokens)
        exact_name_bonus = 0.15 if str(result.get("target_name") or "") in query else 0.0
        nerf_bonus = 0.08 if "너프" in query and result.get("change_type") == "nerf" else 0.0
        buff_bonus = 0.08 if "버프" in query and result.get("change_type") == "buff" else 0.0
        score = float(result["score"]) + (0.08 * overlap) + exact_name_bonus + nerf_bonus + buff_bonus
        adjusted = dict(result)
        adjusted["score"] = round(score, 4)
        reranked.append(adjusted)
    return sorted(reranked, key=lambda item: item["score"], reverse=True)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _import_chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is not installed. Install RAG dependencies with "
            "`pip install -r services/rag/requirements.txt`."
        ) from exc
    return chromadb
