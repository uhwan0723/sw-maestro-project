from collections import deque
from typing import Any

from app.repositories.sqlite import SQLiteRepository


class MultiHopPathService:
    def __init__(self, repository: SQLiteRepository, max_allowed_depth: int = 3):
        self.repository = repository
        self.max_allowed_depth = max_allowed_depth

    def find_card_paths(self, workspace_id: int, card_id: int, depth: int = 2) -> dict[str, Any]:
        max_depth = min(max(1, depth), self.max_allowed_depth)
        cards = {card["id"]: card for card in self.repository.list_cards(workspace_id)}
        if card_id not in cards:
            raise KeyError(f"Card {card_id} not found")

        relations = self.repository.list_relations(workspace_id)
        adjacency = self._build_adjacency(relations)
        paths: list[dict[str, Any]] = []
        queue = deque([(card_id, [card_id], [])])

        while queue:
            current_id, node_ids, edges = queue.popleft()
            if edges:
                paths.append(self._format_path(cards, node_ids, edges))
            if len(edges) >= max_depth:
                continue
            for next_id, edge in adjacency.get(current_id, []):
                if next_id in node_ids:
                    continue
                queue.append((next_id, [*node_ids, next_id], [*edges, edge]))

        paths.sort(key=lambda path: (path["depth"], path["node_ids"]))
        return {
            "start_card_id": card_id,
            "max_depth": max_depth,
            "paths": paths,
        }

    @staticmethod
    def _build_adjacency(relations: list[dict[str, Any]]) -> dict[int, list[tuple[int, dict[str, Any]]]]:
        adjacency: dict[int, list[tuple[int, dict[str, Any]]]] = {}
        for relation in relations:
            source_id = relation["source_card_id"]
            target_id = relation["target_card_id"]
            outgoing = {**relation, "direction": "outgoing"}
            incoming = {**relation, "direction": "incoming"}
            adjacency.setdefault(source_id, []).append((target_id, outgoing))
            adjacency.setdefault(target_id, []).append((source_id, incoming))
        return adjacency

    @staticmethod
    def _format_path(cards: dict[int, dict[str, Any]], node_ids: list[int], edges: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "depth": len(edges),
            "node_ids": node_ids,
            "nodes": [
                {
                    "card_id": node_id,
                    "title": cards[node_id]["title"],
                    "card_type": cards[node_id]["card_type"],
                    "status": cards[node_id]["status"],
                    "confidence": cards[node_id]["confidence"],
                }
                for node_id in node_ids
            ],
            "edges": [
                {
                    "relation_id": edge["id"],
                    "source_card_id": edge["source_card_id"],
                    "target_card_id": edge["target_card_id"],
                    "relation_type": edge["relation_type"],
                    "confidence": edge["confidence"],
                    "direction": edge["direction"],
                }
                for edge in edges
            ],
            "explanation": MultiHopPathService._explain_path(cards, node_ids, edges),
        }

    @staticmethod
    def _explain_path(cards: dict[int, dict[str, Any]], node_ids: list[int], edges: list[dict[str, Any]]) -> str:
        parts = []
        for index, edge in enumerate(edges):
            left = cards[node_ids[index]]["title"]
            right = cards[node_ids[index + 1]]["title"]
            relation = edge["relation_type"]
            parts.append(f"{left} --{relation}--> {right}")
        return " / ".join(parts)
