from typing import Any

from app.repositories.sqlite import SQLiteRepository


class ReviewService:
    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def run(self, workspace_id: int) -> dict[str, Any]:
        cards = self.repository.list_cards(workspace_id)
        relations = self.repository.list_relations(workspace_id)
        targets = self._card_targets(cards) + self._relation_targets(relations)
        targets.sort(key=lambda target: self._priority_rank(target["priority"]))
        return {
            "workspace_id": workspace_id,
            "target_count": len(targets),
            "targets": targets,
            "summary": {
                "needs_review": self._reason_count(targets, "needs_review status"),
                "low_confidence": self._reason_count(targets, "low confidence"),
                "weak_evidence": self._reason_count(targets, "weak evidence"),
                "contradictions": self._reason_count(targets, "contradicts relation candidate"),
            },
        }

    def _card_targets(self, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        targets: list[dict[str, Any]] = []
        for card in cards:
            checks = [
                (card["status"] == "needs_review", "needs_review status", "high"),
                (card["confidence"] == "low", "low confidence", "medium"),
                (len(card["evidence_quote"].strip()) < 12, "weak evidence", "medium"),
            ]
            reasons = [reason for enabled, reason, _ in checks if enabled]
            if not reasons:
                continue
            priority = min(
                (priority for enabled, _, priority in checks if enabled),
                key=self._priority_rank,
            )
            primary_reason = reasons[0]
            targets.append(
                {
                    "card_id": card["id"],
                    "relation_id": None,
                    "reason": primary_reason,
                    "reasons": reasons,
                    "priority": priority,
                    "title": card["title"],
                }
            )
        return targets

    @staticmethod
    def _relation_targets(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "card_id": relation["source_card_id"],
                "relation_id": relation["id"],
                "reason": "contradicts relation candidate",
                "reasons": ["contradicts relation candidate"],
                "priority": "high",
                "title": f"{relation['source_card_id']} contradicts {relation['target_card_id']}",
            }
            for relation in relations
            if relation["relation_type"] == "contradicts"
        ]

    @staticmethod
    def _priority_rank(priority: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)

    @staticmethod
    def _reason_count(targets: list[dict[str, Any]], reason: str) -> int:
        return sum(1 for target in targets if reason in target.get("reasons", [target["reason"]]))
