from typing import Literal

from pydantic import BaseModel, Field


CARD_TYPES = (
    "idea",
    "problem",
    "target_user",
    "hypothesis",
    "evidence",
    "decision",
    "risk",
    "feature",
    "question",
)
CARD_STATUSES = ("proposed", "needs_validation", "validated", "rejected", "decided", "needs_review")
CONFIDENCE_LEVELS = ("low", "medium", "high")
RELATION_TYPES = ("supports", "contradicts", "duplicates", "related_to", "derived_from")

CardType = Literal[
    "idea",
    "problem",
    "target_user",
    "hypothesis",
    "evidence",
    "decision",
    "risk",
    "feature",
    "question",
]
CardStatus = Literal["proposed", "needs_validation", "validated", "rejected", "decided", "needs_review"]
Confidence = Literal["low", "medium", "high"]
RelationType = Literal["supports", "contradicts", "duplicates", "related_to", "derived_from"]


class KnowledgeCardCreate(BaseModel):
    workspace_id: int
    source_document_id: int
    source_chunk_id: int
    card_type: CardType
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: CardStatus = "proposed"
    confidence: Confidence = "medium"


class QAResponse(BaseModel):
    answer: str
    confidence: Confidence
    evidence_cards: list[dict]
    evidence_chunks: list[dict]
    missing_evidence: list[str] = Field(default_factory=list)
