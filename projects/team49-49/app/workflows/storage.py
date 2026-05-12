from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.repositories.sqlite import SQLiteRepository
from app.services.chunking import chunk_text, filter_reusable_chunks
from app.services.extraction import DeterministicCardExtractor
from app.services.parsing import parse_document


class StorageState(TypedDict, total=False):
    workspace_id: int
    filename: str
    content: str
    source_type: str
    source_url: str
    external_id: str
    document: dict[str, Any]
    chunks: list[str]
    stored_chunks: list[dict[str, Any]]
    reusable_chunks: list[str]
    card_count: int
    new_card_ids: list[int]
    needs_review_count: int
    result: dict[str, Any]


class StorageWorkflow:
    def __init__(
        self,
        repository: SQLiteRepository,
        extractor: DeterministicCardExtractor | None = None,
    ):
        self.repository = repository
        self.extractor = extractor or DeterministicCardExtractor()
        self.graph = self._build_graph()

    def ingest_bytes(
        self,
        workspace_id: int,
        filename: str,
        content: bytes,
        source_type: str = "upload",
        source_url: str = "",
        external_id: str = "",
    ) -> dict[str, Any]:
        text = parse_document(filename, content)
        return self.ingest_text(
            workspace_id=workspace_id,
            filename=filename,
            content=text,
            source_type=source_type,
            source_url=source_url,
            external_id=external_id,
        )

    def ingest_text(
        self,
        workspace_id: int,
        filename: str,
        content: str,
        source_type: str = "manual",
        source_url: str = "",
        external_id: str = "",
    ) -> dict[str, Any]:
        state = self.graph.invoke(
            {
                "workspace_id": workspace_id,
                "filename": filename,
                "content": content,
                "source_type": source_type,
                "source_url": source_url,
                "external_id": external_id,
            }
        )
        return state["result"]

    def _build_graph(self):
        graph = StateGraph(StorageState)
        graph.add_node("save_raw_document", self._save_raw_document)
        graph.add_node("chunk_document", self._chunk_document)
        graph.add_node("extract_cards", self._extract_cards)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "save_raw_document")
        graph.add_edge("save_raw_document", "chunk_document")
        graph.add_edge("chunk_document", "extract_cards")
        graph.add_edge("extract_cards", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _save_raw_document(self, state: StorageState) -> StorageState:
        filename = state["filename"]
        document_type = Path(filename).suffix.lower().lstrip(".") or "text"
        document = self.repository.create_raw_document(
            workspace_id=state["workspace_id"],
            filename=filename,
            document_type=document_type,
            content=state["content"],
            source_type=state.get("source_type") or "manual",
            source_url=state.get("source_url") or "",
            external_id=state.get("external_id") or "",
        )
        return {"document": document}

    def _chunk_document(self, state: StorageState) -> StorageState:
        chunks = chunk_text(state["content"])
        stored_chunks = self.repository.create_chunks(
            document_id=state["document"]["id"],
            workspace_id=state["workspace_id"],
            contents=chunks,
        )
        return {
            "chunks": chunks,
            "stored_chunks": stored_chunks,
            "reusable_chunks": filter_reusable_chunks(chunks),
        }

    def _extract_cards(self, state: StorageState) -> StorageState:
        reusable_chunks = set(state["reusable_chunks"])
        card_count = 0
        needs_review_count = 0
        new_card_ids = []
        for chunk in state["stored_chunks"]:
            if chunk["content"] not in reusable_chunks:
                continue
            cards = self.extractor.extract(
                chunk=chunk["content"],
                workspace_id=state["workspace_id"],
                source_document_id=state["document"]["id"],
                source_chunk_id=chunk["id"],
            )
            for card in cards:
                stored_card = self.repository.create_knowledge_card(**card.model_dump())
                new_card_ids.append(stored_card["id"])
                if stored_card["status"] == "needs_review":
                    needs_review_count += 1
                card_count += 1
        return {
            "card_count": card_count,
            "new_card_ids": new_card_ids,
            "needs_review_count": needs_review_count,
        }

    def _finalize(self, state: StorageState) -> StorageState:
        return {
            "result": {
                "document_id": state["document"]["id"],
                "chunk_count": len(state["stored_chunks"]),
                "card_count": state["card_count"],
                "skipped_chunk_count": len(state["stored_chunks"]) - len(set(state["reusable_chunks"])),
                "new_card_ids": state.get("new_card_ids", []),
                "needs_review_count": state.get("needs_review_count", 0),
            }
        }
