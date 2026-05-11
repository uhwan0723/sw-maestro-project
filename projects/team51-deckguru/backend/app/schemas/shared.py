"""공통 schema — 07-data-contracts.md §1, §2 단일 진실 소스.

Backend / Strategy / RAG / Research 모두 본 모듈을 import한다.
변경 시 07-data-contracts.md를 함께 업데이트하고 CODEOWNERS 리뷰 강제.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

# §1.1 ~ §1.9 공통 enum (Literal 별칭으로 노출)

Tier = Literal[
    "IRON", "BRONZE", "SILVER", "GOLD",
    "PLATINUM", "EMERALD", "DIAMOND", "MASTER+",
]

PlayStyle = Literal[
    "stable_top4",
    "high_risk_first",
    "easy_beginner",
    "flexible",
]

Intent = Literal[
    "recommend_deck",
    "deck_playstyle",
    "item_pivot",
    "patch_summary",
    "other",
]

Phase = Literal["early", "mid", "late"]
Difficulty = Literal["easy", "medium", "hard"]
Confidence = Literal["high", "medium", "low"]

IndexName = Literal[
    "units", "traits", "items", "augments",
    "deck_templates", "playbook", "patch_summary", "glossary",
]

ToolName = Literal["web_search", "fetch_page"]

SourceKind = Literal[
    "patch_note_official", "meta_site", "community_post",
]


# §2.1 Source

class Source(BaseModel):
    title: str = Field(min_length=1)
    url: HttpUrl
    published_at: str | None = None
    snippet: str = Field(max_length=200)
    source_kind: SourceKind | None = None


# §2.2 RagChunk

class RagChunk(BaseModel):
    id: str
    index: IndexName
    text: str
    metadata: dict = Field(default_factory=dict)
    score: float = Field(ge=0.0, le=1.0)


# §2.3 WebFact (Live Research 출력)

class WebFact(BaseModel):
    text: str = Field(max_length=400)
    quote: str = Field(max_length=300)
    source_url: HttpUrl
    source_title: str | None = None
    published_at: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


# §2.4 PlaybookStep

class PlaybookStep(BaseModel):
    phase: Phase
    instruction: str = Field(min_length=1, max_length=200)


# §2.5 DeckRecommendation — verify_grounding 통과한 최종 형태

class DeckRecommendation(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    difficulty: Difficulty
    core_units: list[str] = Field(min_length=3, max_length=9)
    key_items: list[str] = Field(min_length=1, max_length=6)
    augment_direction: str = Field(max_length=120)
    playbook: list[PlaybookStep] = Field(min_length=1)
    good_conditions: list[str] = Field(min_length=1)
    avoid_conditions: list[str] = Field(default_factory=list)
    fallback_plan: str = Field(max_length=200)
    rationale: str = Field(max_length=300)


# DeckDraft — analyze_meta 출력 (검증 전 후보)

class DeckDraft(BaseModel):
    name: str
    difficulty: Difficulty | None = None
    core_units: list[str] = Field(default_factory=list)
    key_items: list[str] = Field(default_factory=list)
    evidence_chunk_ids: list[str] = Field(
        default_factory=list,
        description="이 후보의 근거가 된 RagChunk.id 또는 WebFact source_url",
    )


__all__ = [
    "Tier", "PlayStyle", "Intent", "Phase", "Difficulty", "Confidence",
    "IndexName", "ToolName", "SourceKind",
    "Source", "RagChunk", "WebFact", "PlaybookStep", "DeckRecommendation", "DeckDraft",
]
