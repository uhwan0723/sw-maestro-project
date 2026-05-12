from typing import Any

from app.repositories.sqlite import SQLiteRepository


class KnowledgeGraphService:
    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def build_workspace_graph(self, workspace_id: int) -> dict[str, list[dict[str, Any]]]:
        documents = self.repository.list_raw_documents(workspace_id)
        cards = self.repository.list_cards(workspace_id)
        relations = self.repository.list_relations(workspace_id)
        nodes: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []

        for document in documents:
            nodes.append(
                {
                    "id": f"doc:{document['id']}",
                    "type": "document",
                    "label": document["filename"],
                    "document_type": document["document_type"],
                }
            )

        for document_link in self.repository.list_raw_document_links(workspace_id):
            links.append(
                {
                    "source": f"doc:{document_link['source_document_id']}",
                    "target": f"doc:{document_link['target_document_id']}",
                    "type": document_link["relation_type"],
                    "label": document_link["relation_type"],
                    "confidence": document_link["confidence"],
                }
            )

        for card in cards:
            nodes.append(
                {
                    "id": f"card:{card['id']}",
                    "type": "card",
                    "label": card["title"],
                    "card_type": card["card_type"],
                    "status": card["status"],
                    "confidence": card["confidence"],
                }
            )
            links.append(
                {
                    "source": f"doc:{card['source_document_id']}",
                    "target": f"card:{card['id']}",
                    "type": "contains",
                    "label": "contains",
                }
            )

        cards_by_id = {card["id"]: card for card in cards}
        document_links: set[tuple[int, int, str]] = set()
        for relation in relations:
            source_card = cards_by_id.get(relation["source_card_id"])
            target_card = cards_by_id.get(relation["target_card_id"])
            if not source_card or not target_card:
                continue
            links.append(
                {
                    "source": f"card:{relation['source_card_id']}",
                    "target": f"card:{relation['target_card_id']}",
                    "type": relation["relation_type"],
                    "label": relation["relation_type"],
                    "confidence": relation["confidence"],
                }
            )
            source_doc_id = source_card["source_document_id"]
            target_doc_id = target_card["source_document_id"]
            if source_doc_id != target_doc_id:
                ordered = tuple(sorted((source_doc_id, target_doc_id)))
                document_links.add((ordered[0], ordered[1], relation["relation_type"]))

        for source_doc_id, target_doc_id, relation_type in sorted(document_links):
            links.append(
                {
                    "source": f"doc:{source_doc_id}",
                    "target": f"doc:{target_doc_id}",
                    "type": "document_link",
                    "label": relation_type,
                }
            )

        return {"nodes": nodes, "links": links}
