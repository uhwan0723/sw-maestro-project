from typing import Any


def _card_fields(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card["id"],
        "card_type": card["card_type"],
        "title": card["title"],
        "summary": card["summary"],
        "evidence_quote": card["evidence_quote"],
        "keywords": card["keywords"],
        "tags": card["tags"],
        "status": card["status"],
        "confidence": card["confidence"],
        "source_document_id": card["source_document_id"],
        "source_chunk_id": card["source_chunk_id"],
    }


def build_qa_context_bundle(
    workspace_id: int,
    question: str,
    cards: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    relations: list[dict[str, Any]] | None = None,
    neighbor_cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    relations = relations or []
    neighbor_cards = neighbor_cards or []
    return {
        "schema_version": "qa_context_bundle.v1",
        "workspace_id": workspace_id,
        "question": question,
        "cards": [_card_fields(card) for card in cards],
        "chunks": [
            {
                "id": chunk["id"],
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "token_estimate": chunk["token_estimate"],
            }
            for chunk in chunks
        ],
        "relations": [
            {
                "id": r["id"],
                "source_card_id": r["source_card_id"],
                "target_card_id": r["target_card_id"],
                "relation_type": r["relation_type"],
                "reason": r["reason"],
                "confidence": r["confidence"],
            }
            for r in (relations or [])
        ],
        "neighbor_cards": [_card_fields(card) for card in (neighbor_cards or [])],
    }
