"""LangGraph State 정의 — 3 파트 공용 인터페이스 계약.

수정 시 합의 필수. 키 이름·타입 변경은 A·B·C 협의 후만.

채우는 주체:
  - 외부 입력: session_id, user_query, history
  - A (LLM):   domain, case_type, needs_settlement, classification_confidence,
              clarification_question, answer_text, citations
  - B (검색): retrieved_docs
  - C (룰):   guide_steps, settlement, confidence_score, recommend_lawyer,
              situation_summary, fallback_reason
"""
from typing import Literal, Optional, TypedDict

from app.taxonomy import CaseType


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class RetrievedDoc(TypedDict):
    doc_id: str
    type: Literal["법령", "판례", "사례"]
    title: str
    content: str
    case_types: list[str]
    score: float
    settlement_amount: Optional[int]


class Settlement(TypedDict):
    min: int
    median: int
    max: int
    sample_size: int
    basis: str


class Citation(TypedDict):
    marker_idx: int
    doc_id: str


class LegalState(TypedDict, total=False):
    # 외부 입력
    session_id: str
    user_query: str
    history: list[ChatMessage]

    # A — classify
    domain: str
    case_type: Optional[CaseType]
    needs_settlement: bool
    classification_confidence: float

    # A — clarify
    clarification_question: Optional[str]

    # B — retrieve
    retrieved_docs: list[RetrievedDoc]

    # C — guide / settlement
    guide_steps: Optional[list[str]]
    settlement: Optional[Settlement]

    # A — generate
    answer_text: str
    citations: list[Citation]

    # C — post_check / fallback
    confidence_score: float
    recommend_lawyer: bool
    situation_summary: Optional[str]
    fallback_reason: Optional[str]
