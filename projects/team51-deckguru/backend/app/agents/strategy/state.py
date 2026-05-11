"""StrategyState — 02-spec §2.

Pydantic v2. LangGraph는 dict-like state도 지원하지만 본 프로젝트는
schema 강제를 위해 Pydantic 모델을 그대로 state 타입으로 사용.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.shared import (
    Confidence,
    DeckDraft,
    DeckRecommendation,
    Intent,
    PlayStyle,
    RagChunk,
    Source,
    Tier,
    WebFact,
)


class StrategyState(BaseModel):
    request_id: str
    patch_version: str

    # input
    tier: Tier
    play_style: PlayStyle
    question: str

    # intent
    intent: Intent | None = None
    extracted_keywords: list[str] = Field(default_factory=list)

    # retrieval
    rag_chunks: list[RagChunk] = Field(default_factory=list)
    rag_avg_score: float = 0.0

    # live research (optional)
    need_live: bool = False
    web_facts: list[WebFact] = Field(default_factory=list)
    research_steps: int = 0

    # synthesis
    meta_summary: str | None = None
    candidate_decks: list[DeckDraft] = Field(default_factory=list)
    final_decks: list[DeckRecommendation] = Field(default_factory=list)

    # meta
    sources: list[Source] = Field(default_factory=list)
    confidence: Confidence = "medium"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # observability — DEMO_MODE 응답에만 노출
    node_latencies_ms: dict[str, int] = Field(default_factory=dict)
