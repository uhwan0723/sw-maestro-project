from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.chroma_service import ChromaRagService, count_chroma_collections
from app.rag.service import RagUnavailableError


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [float(len(text) or 1)]


class FakeCollection:
    def __init__(self, *, query_result=None, metadatas=None, count=0):
        self.query_result = query_result or {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        self.metadatas = metadatas or []
        self.count_value = count
        self.query_calls = []
        self.get_calls = 0

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return self.query_result

    def get(self, **kwargs):
        self.get_calls += 1
        return {"metadatas": self.metadatas}

    def count(self):
        return self.count_value


class FakeClient:
    def __init__(self, collections):
        self.collections = collections

    def get_collection(self, name: str):
        if name not in self.collections:
            raise ValueError(name)
        return self.collections[name]


def test_search_filters_dedupes_and_sorts_by_similarity():
    collection = FakeCollection(
        query_result={
            "ids": [["a", "b", "a", "low"]],
            "documents": [["first", "second", "better first", "weak"]],
            "metadatas": [[
                {"patch_version": "17.2", "name": "A"},
                {"patch_version": "17.2b", "name": "B"},
                {"patch_version": "17.2", "name": "A"},
                {"patch_version": "all", "name": "Low"},
            ]],
            "distances": [[0.4, 0.1, 0.2, 0.95]],
        }
    )
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({"deck_templates": collection}),
        embedder=FakeEmbedder(),
        min_score=0.2,
    )

    chunks = service.search("deck_templates", "마스터 이", k=5, patch_version="17.2")

    assert [chunk.id for chunk in chunks] == ["b", "a"]
    assert chunks[0].score == pytest.approx(0.9)
    assert chunks[1].text == "better first"
    assert collection.query_calls[0]["where"]["patch_version"]["$in"][:2] == ["17.2", "17.2a"]
    assert "all" in collection.query_calls[0]["where"]["patch_version"]["$in"]


def test_multi_search_dedupes_across_indices():
    deck_collection = FakeCollection(
        query_result={
            "ids": [["same"]],
            "documents": [["deck"]],
            "metadatas": [[{"patch_version": "17.2"}]],
            "distances": [[0.3]],
        }
    )
    patch_collection = FakeCollection(
        query_result={
            "ids": [["same", "other"]],
            "documents": [["patch", "other"]],
            "metadatas": [[{"patch_version": "17.2"}, {"patch_version": "all"}]],
            "distances": [[0.1, 0.5]],
        }
    )
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({"deck_templates": deck_collection, "patch_summary": patch_collection}),
        embedder=FakeEmbedder(),
    )

    chunks = service.multi_search(
        [("deck_templates", "q", 3), ("patch_summary", "q", 3)],
        patch_version="17.2",
    )

    assert [chunk.id for chunk in chunks] == ["same", "other"]
    assert chunks[0].index == "patch_summary"


def test_multi_search_skips_unavailable_secondary_collections():
    deck_collection = FakeCollection(
        query_result={
            "ids": [["deck"]],
            "documents": [["deck"]],
            "metadatas": [[{"patch_version": "17.2"}]],
            "distances": [[0.2]],
        }
    )
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({"deck_templates": deck_collection}),
        embedder=FakeEmbedder(),
    )

    chunks = service.multi_search(
        [("deck_templates", "q", 3), ("augments", "q", 3), ("traits", "q", 3)],
        patch_version="17.2",
    )

    assert [chunk.id for chunk in chunks] == ["deck"]


def test_multi_search_raises_when_all_planned_collections_are_unavailable():
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({}),
        embedder=FakeEmbedder(),
    )

    with pytest.raises(RagUnavailableError, match="all planned RAG collections"):
        service.multi_search(
            [("augments", "q", 3), ("traits", "q", 3)],
            patch_version="17.2",
        )


def test_get_whitelist_uses_ttl_cache():
    units = FakeCollection(metadatas=[{"name": "마스터 이"}, {"name": "킨드레드"}])
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({"units": units}),
        embedder=FakeEmbedder(),
    )

    first = service.get_whitelist("17.2")
    second = service.get_whitelist("17.2")

    assert first["units"] == {"마스터 이", "킨드레드"}
    assert second["units"] == {"마스터 이", "킨드레드"}
    assert first["items"] == set()
    assert units.get_calls == 1


def test_missing_search_collection_is_unavailable():
    service = ChromaRagService(
        persist_path=Path("unused"),
        client=FakeClient({}),
        embedder=FakeEmbedder(),
    )

    with pytest.raises(RagUnavailableError):
        service.search("deck_templates", "q", k=1, patch_version="17.2")


def test_count_chroma_collections_returns_zero_without_path(tmp_path):
    assert all(count == 0 for count in count_chroma_collections(tmp_path / "missing").values())
