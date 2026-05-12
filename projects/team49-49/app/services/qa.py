from typing import Any

from app.repositories.sqlite import SQLiteRepository
from app.services.context_bundle import build_qa_context_bundle
from app.services.langgraph_remote import RemoteLangGraphRunner
from app.services.retrieval import RetrievalService

INSUFFICIENT_CONTEXT_MESSAGE = "현재까지 저장된 팀 컨텍스트에서는 관련된 논의나 근거를 찾을 수 없습니다."
REMOTE_LANGGRAPH_NOT_CONFIGURED_MESSAGE = (
    "LangGraph Q&A assistant가 연결되어 있지 않아요. "
    "LANGGRAPH_DEPLOYMENT_URL, LANGSMITH_API_KEY, LANGGRAPH_QA_ASSISTANT_ID를 설정해 주세요."
)
REMOTE_LANGGRAPH_FAILED_MESSAGE = (
    "LangGraph Q&A assistant 호출에 실패했어요. "
    "연결 설정과 LangGraph deployment 상태를 확인해 주세요."
)


class GroundedQAService:
    def __init__(
        self,
        repository: SQLiteRepository,
        retrieval: RetrievalService | None = None,
        remote_langgraph_client: RemoteLangGraphRunner | None = None,
        remote_qa_assistant_id: str = "",
    ):
        self.repository = repository
        self.retrieval = retrieval or RetrievalService(repository)
        self.remote_langgraph_client = remote_langgraph_client
        self.remote_qa_assistant_id = remote_qa_assistant_id

    def answer(self, workspace_id: int, question: str) -> dict[str, Any]:
        search = self.retrieval.search(workspace_id=workspace_id, query=question, top_k=4)
        return self.answer_from_search(workspace_id=workspace_id, question=question, search=search)

    def answer_from_search(self, workspace_id: int, question: str, search: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        cards = search["cards"]
        chunks = search["chunks"]
        if not cards and not chunks:
            response = {
                "answer": INSUFFICIENT_CONTEXT_MESSAGE,
                "confidence": "low",
                "evidence_cards": [],
                "evidence_chunks": [],
                "relation_evidence": [],
                "missing_evidence": ["질문과 관련된 저장 컨텍스트가 부족합니다."],
            }
            self.repository.create_chat_history(
                workspace_id=workspace_id,
                question=question,
                answer=response["answer"],
                referenced_card_ids=[],
                referenced_chunk_ids=[],
            )
            return response

        card_ids = [card["id"] for card in cards]
        expansion = self.retrieval.expand_with_neighbor_cards(workspace_id, card_ids)
        relations = expansion["relations"]
        neighbor_cards = expansion["neighbor_cards"]

        evidence_cards = [self._card_evidence(card) for card in cards]
        evidence_chunks = [self._chunk_evidence(chunk) for chunk in chunks]
        relation_evidence = [self._relation_evidence(r) for r in relations]
        context_cards = self._merge_cards(cards, neighbor_cards)
        evidence_cards = [self._card_evidence(card) for card in context_cards]

        if not self._remote_is_configured():
            return self._persist_and_return(
                workspace_id=workspace_id,
                question=question,
                answer=REMOTE_LANGGRAPH_NOT_CONFIGURED_MESSAGE,
                confidence="low",
                evidence_cards=evidence_cards,
                evidence_chunks=evidence_chunks,
                relation_evidence=relation_evidence,
                missing_evidence=["LangGraph Q&A assistant 연결 정보가 없습니다."],
                cards=context_cards,
                chunks=chunks,
            )

        remote_response = self._remote_qa_response(workspace_id, question, cards, chunks, relations, neighbor_cards)
        if not remote_response:
            return self._persist_and_return(
                workspace_id=workspace_id,
                question=question,
                answer=REMOTE_LANGGRAPH_FAILED_MESSAGE,
                confidence="low",
                evidence_cards=evidence_cards,
                evidence_chunks=evidence_chunks,
                relation_evidence=relation_evidence,
                missing_evidence=["LangGraph Q&A assistant가 유효한 답변을 반환하지 않았습니다."],
                cards=context_cards,
                chunks=chunks,
            )

        answer = remote_response["answer"]
        confidence = str(remote_response.get("confidence", "low"))
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        missing_evidence = (
            remote_response.get("missing_evidence")
            if isinstance(remote_response.get("missing_evidence"), list)
            else []
        )

        return self._persist_and_return(
            workspace_id=workspace_id,
            question=question,
            answer=answer,
            confidence=confidence,
            evidence_cards=evidence_cards,
            evidence_chunks=evidence_chunks,
            relation_evidence=relation_evidence,
            missing_evidence=missing_evidence,
            cards=context_cards,
            chunks=chunks,
        )

    def _card_evidence(self, card: dict[str, Any]) -> dict[str, Any]:
        document = self.repository.get_raw_document(card["source_document_id"])
        return {
            "card_id": card["id"],
            "title": card["title"],
            "source_document": document["filename"],
            "evidence_quote": card["evidence_quote"],
        }

    def _chunk_evidence(self, chunk: dict[str, Any]) -> dict[str, Any]:
        document = self.repository.get_raw_document(chunk["document_id"])
        return {
            "chunk_id": chunk["id"],
            "source_document": document["filename"],
            "quote": chunk["content"],
        }

    def _relation_evidence(self, relation: dict[str, Any]) -> dict[str, Any]:
        return {
            "relation_id": relation["id"],
            "source_card_id": relation["source_card_id"],
            "target_card_id": relation["target_card_id"],
            "relation_type": relation["relation_type"],
            "reason": relation["reason"],
            "confidence": relation["confidence"],
        }

    def _persist_and_return(
        self,
        workspace_id: int,
        question: str,
        answer: str,
        confidence: str,
        evidence_cards: list[dict[str, Any]],
        evidence_chunks: list[dict[str, Any]],
        relation_evidence: list[dict[str, Any]],
        missing_evidence: list[str],
        cards: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.repository.create_chat_history(
            workspace_id=workspace_id,
            question=question,
            answer=answer,
            referenced_card_ids=[card["id"] for card in cards],
            referenced_chunk_ids=[chunk["id"] for chunk in chunks],
        )
        return {
            "answer": answer,
            "confidence": confidence,
            "evidence_cards": evidence_cards,
            "evidence_chunks": evidence_chunks,
            "relation_evidence": relation_evidence,
            "missing_evidence": missing_evidence,
        }

    def _remote_is_configured(self) -> bool:
        return bool(
            self.remote_langgraph_client
            and self.remote_langgraph_client.is_configured(self.remote_qa_assistant_id)
        )

    def _remote_qa_response(
        self,
        workspace_id: int,
        question: str,
        cards: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        relations: list[dict[str, Any]] | None = None,
        neighbor_cards: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self._remote_is_configured():
            return {}

        payload = build_qa_context_bundle(
            workspace_id=workspace_id,
            question=question,
            cards=cards,
            chunks=chunks,
            relations=relations,
            neighbor_cards=neighbor_cards,
        )
        try:
            raw_result = self.remote_langgraph_client.run(self.remote_qa_assistant_id, payload)
        except Exception:
            return {}
        return self._extract_answer_payload(raw_result)

    def _extract_answer_payload(self, raw_result: dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw_result.get("answer"), str):
            return raw_result
        for value in raw_result.values():
            if not isinstance(value, dict):
                continue
            if isinstance(value.get("result"), dict) and isinstance(value["result"].get("answer"), str):
                return value["result"]
            if isinstance(value.get("answer"), str):
                return value
        return {}

    def _neighbor_cards(
        self,
        workspace_id: int,
        cards: list[dict[str, Any]],
        relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        retrieved_ids = {card["id"] for card in cards}
        neighbor_ids: set[int] = set()
        for relation in relations:
            for card_id in (relation["source_card_id"], relation["target_card_id"]):
                if card_id not in retrieved_ids:
                    neighbor_ids.add(card_id)
        cards_by_id = {card["id"]: card for card in self.repository.list_cards(workspace_id)}
        return [cards_by_id[card_id] for card_id in sorted(neighbor_ids) if card_id in cards_by_id]

    @staticmethod
    def _merge_cards(cards: list[dict[str, Any]], neighbor_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[int] = set()
        for card in [*cards, *neighbor_cards]:
            if card["id"] in seen:
                continue
            merged.append(card)
            seen.add(card["id"])
        return merged
