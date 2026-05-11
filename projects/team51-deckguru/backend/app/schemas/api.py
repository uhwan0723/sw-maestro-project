"""Backend API schema — 07-data-contracts.md §4, §5.

POST /api/recommend 요청/응답.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.shared import (
    Confidence,
    DeckRecommendation,
    Intent,
    PlayStyle,
    Source,
    Tier,
)


# §5.1 Request

class RecommendRequest(BaseModel):
    tier: Tier
    play_style: PlayStyle
    question: str = Field(min_length=1, max_length=500)


# §4 Response

class DebugInfo(BaseModel):
    react_steps: int = Field(default=0, ge=0, le=5)
    rag_avg_score: float = Field(default=0.0, ge=0.0, le=1.0)
    tier2_triggered: bool = False
    node_latencies_ms: dict[str, int] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    request_id: str
    patch_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    intent: Intent
    meta_summary: str = Field(max_length=400)
    decks: list[DeckRecommendation] = Field(default_factory=list, max_length=3)
    sources: list[Source] = Field(default_factory=list)
    confidence: Confidence = "medium"
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime
    debug: DebugInfo | None = None


# §5.4 Feedback

class FeedbackRequest(BaseModel):
    request_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    deck_clicked: str | None = None


# 에러 응답

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


__all__ = [
    "RecommendRequest",
    "RecommendationResponse",
    "DebugInfo",
    "FeedbackRequest",
    "ErrorDetail",
    "ErrorResponse",
]
