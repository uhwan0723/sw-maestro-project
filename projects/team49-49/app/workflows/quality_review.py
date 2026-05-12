import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.repositories.sqlite import SQLiteRepository
from app.services.llm import LLMClient, NoOpLLMClient


class QualityReviewState(TypedDict, total=False):
    workspace_id: int
    all_cards: list[dict[str, Any]]
    all_relations: list[dict[str, Any]]
    connected_card_ids: set[int]
    candidates: list[dict[str, Any]]
    review_targets: list[dict[str, Any]]
    result: dict[str, Any]


_SYSTEM_PROMPT = (
    "당신은 기획 카드 품질 검토 전문가입니다. "
    "문제점과 개선 방향을 한국어로 간결하게 답하세요. "
    'JSON 형식으로만 답하세요: {"issue": "...", "suggestion": "..."}'
)


class QualityReviewWorkflow:
    def __init__(
        self,
        repository: SQLiteRepository,
        llm_client: LLMClient | None = None,
    ):
        self.repository = repository
        self.llm_client = llm_client or NoOpLLMClient()
        self.graph = self._build_graph()

    def run(self, workspace_id: int) -> dict[str, Any]:
        state = self.graph.invoke({"workspace_id": workspace_id})
        return state["result"]

    def _build_graph(self):
        graph = StateGraph(QualityReviewState)
        graph.add_node("collect_candidates", self._collect_candidates)
        graph.add_node("analyze_cards", self._analyze_cards)
        graph.add_node("update_statuses", self._update_statuses)
        graph.add_node("generate_summary", self._generate_summary)
        graph.add_edge(START, "collect_candidates")
        graph.add_edge("collect_candidates", "analyze_cards")
        graph.add_edge("analyze_cards", "update_statuses")
        graph.add_edge("update_statuses", "generate_summary")
        graph.add_edge("generate_summary", END)
        return graph.compile()

    def _collect_candidates(self, state: QualityReviewState) -> QualityReviewState:
        workspace_id = state["workspace_id"]
        all_cards = self.repository.list_cards(workspace_id)
        all_relations = self.repository.list_relations(workspace_id)
        connected_ids: set[int] = {r["source_card_id"] for r in all_relations} | {r["target_card_id"] for r in all_relations}

        candidates = [
            card for card in all_cards
            if card["confidence"] == "low"
            or card["status"] in ("needs_review", "needs_validation")
            or card["id"] not in connected_ids
            or len(card["evidence_quote"]) < 30
        ]
        return {
            "all_cards": all_cards,
            "all_relations": all_relations,
            "connected_card_ids": connected_ids,
            "candidates": candidates,
        }

    def _analyze_cards(self, state: QualityReviewState) -> QualityReviewState:
        connected_ids = state.get("connected_card_ids", set())
        review_targets: list[dict[str, Any]] = []

        for card in state["candidates"]:
            relation_count = sum(
                1 for r in state["all_relations"]
                if r["source_card_id"] == card["id"] or r["target_card_id"] == card["id"]
            )
            issue, suggestion = self._analyze_single_card(card, relation_count, connected_ids)
            reasons = _review_reasons(card, connected_ids)
            review_targets.append({
                "card_id": card["id"],
                "card_type": card["card_type"],
                "title": card["title"],
                "reason": reasons[0],
                "reasons": reasons,
                "priority": "high" if "needs_review status" in reasons or "low confidence" in reasons else "medium",
                "issue": issue,
                "suggestion": suggestion,
            })

        return {"review_targets": review_targets}

    def _analyze_single_card(
        self,
        card: dict[str, Any],
        relation_count: int,
        connected_ids: set[int],
    ) -> tuple[str, str]:
        llm_text = self.llm_client.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"카드 타입: {card['card_type']}\n"
                f"제목: {card['title']}\n"
                f"요약: {card['summary']}\n"
                f"근거 인용: {card['evidence_quote']}\n"
                f"현재 상태: {card['status']} / confidence: {card['confidence']}\n"
                f"연결 관계 수: {relation_count}개\n\n"
                "이 카드의 주요 문제점 1가지와 개선 제안 1가지를 알려주세요."
            ),
        )
        if llm_text:
            parsed = _parse_llm_json(llm_text)
            if parsed:
                return str(parsed.get("issue", "")), str(parsed.get("suggestion", ""))

        return _rule_based_issue(card, connected_ids)

    def _update_statuses(self, state: QualityReviewState) -> QualityReviewState:
        all_cards_by_id = {c["id"]: c for c in state["all_cards"]}
        for target in state["review_targets"]:
            card = all_cards_by_id.get(target["card_id"])
            if card and card["status"] not in ("needs_review", "rejected", "decided"):
                self.repository.update_card(target["card_id"], status="needs_review")
        return {}

    def _generate_summary(self, state: QualityReviewState) -> QualityReviewState:
        total = len(state["all_cards"])
        reviewed = len(state["review_targets"])
        summary = (
            f"전체 {total}개 카드 중 {reviewed}개 검토 필요."
            if reviewed
            else f"전체 {total}개 카드 모두 품질 기준을 통과했습니다."
        )
        return {
            "result": {
                "workspace_id": state["workspace_id"],
                "total_cards": total,
                "reviewed_count": reviewed,
                "review_targets": state["review_targets"],
                "quality_summary": summary,
                "target_count": reviewed,
                "targets": state["review_targets"],
                "summary": {
                    "needs_review": sum(1 for target in state["review_targets"] if "needs_review status" in target["reasons"]),
                    "low_confidence": sum(1 for target in state["review_targets"] if "low confidence" in target["reasons"]),
                },
            }
        }


def _parse_llm_json(text: str) -> dict[str, str] | None:
    try:
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _rule_based_issue(card: dict[str, Any], connected_ids: set[int]) -> tuple[str, str]:
    if card["id"] not in connected_ids and card["card_type"] in ("hypothesis", "decision"):
        return "근거 카드 미연결", "이 카드를 뒷받침하는 evidence 카드가 필요합니다"
    if card["confidence"] == "low" and card["id"] not in connected_ids:
        return "근거 연결 없음", "관련 evidence 카드를 추가하거나 연결하세요"
    if len(card["evidence_quote"]) < 30:
        return "근거 인용 불충분", "원문에서 더 구체적인 근거를 인용하세요"
    return "검토 필요", "카드 내용을 팀과 함께 검토하세요"


def _review_reasons(card: dict[str, Any], connected_ids: set[int]) -> list[str]:
    reasons: list[str] = []
    if card["status"] == "needs_review":
        reasons.append("needs_review status")
    elif card["status"] == "needs_validation":
        reasons.append("needs_validation status")
    if card["confidence"] == "low":
        reasons.append("low confidence")
    if not reasons and card["id"] not in connected_ids:
        reasons.append("no relation")
    if not reasons and len(card["evidence_quote"]) < 30:
        reasons.append("short evidence")
    return reasons or ["review needed"]
