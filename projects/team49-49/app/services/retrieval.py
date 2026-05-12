from typing import Any

from app.repositories.sqlite import SQLiteRepository
from app.services.vector_store import LocalVectorStore


class RetrievalService:
    def __init__(self, repository: SQLiteRepository, vector_store: LocalVectorStore | None = None):
        self.repository = repository
        self.vector_store = vector_store or LocalVectorStore()

    def search(self, workspace_id: int, query: str, top_k: int = 5) -> dict[str, list[dict[str, Any]]]:
        cards = self.repository.list_cards(workspace_id)
        chunks = self.repository.list_chunks(workspace_id)
        card_items = [
            {
                **card,
                "search_text": f"{card['title']} {card['summary']} {' '.join(card['keywords'])} {' '.join(card['tags'])}",
            }
            for card in cards
        ]
        chunk_items = [{**chunk, "search_text": chunk["content"]} for chunk in chunks]
        ranked_cards = self.vector_store.rank(query, card_items, text_key="search_text", top_k=top_k)
        ranked_chunks = self.vector_store.rank(query, chunk_items, text_key="search_text", top_k=top_k)
        for card in ranked_cards:
            card.pop("search_text", None)
        for chunk in ranked_chunks:
            chunk.pop("search_text", None)
        return {"cards": ranked_cards, "chunks": ranked_chunks}

    def expand_one_hop_relations(self, workspace_id: int, card_ids: list[int]) -> list[dict[str, Any]]:
        seen_relation_ids: set[int] = set()
        relations: list[dict[str, Any]] = []
        for card_id in card_ids:
            for relation in self.repository.list_relations(workspace_id, card_id=card_id):
                if relation["id"] not in seen_relation_ids:
                    seen_relation_ids.add(relation["id"])
                    relations.append(relation)
        return relations

    def expand_with_neighbor_cards(
        self, workspace_id: int, card_ids: list[int]
    ) -> dict[str, list[dict[str, Any]]]:
        relations = self.expand_one_hop_relations(workspace_id, card_ids)
        seed_ids = set(card_ids)
        neighbor_ids: set[int] = set()
        for r in relations:
            for nid in (r["source_card_id"], r["target_card_id"]):
                if nid not in seed_ids:
                    neighbor_ids.add(nid)
        neighbor_cards: list[dict[str, Any]] = []
        for nid in neighbor_ids:
            try:
                neighbor_cards.append(self.repository.get_card(nid))
            except KeyError:
                pass
        return {"relations": relations, "neighbor_cards": neighbor_cards}
