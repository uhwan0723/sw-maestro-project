from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import RequestType, SectorCode
from app.schemas.analysis import KeyEvidence
from app.schemas.chat import ChatTurn
from app.schemas.common import SourceInfo, WarningMessage


class TickerIndicatorContext(BaseModel):
    ticker: str
    price: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    sources: list[str] = Field(default_factory=list)


class SectorComparisonContext(BaseModel):
    ticker_count: int = 0
    price_count: int = 0
    change_percent_count: int = 0
    volume_count: int = 0
    average_change_percent: float | None = None
    rising_count: int = 0
    falling_count: int = 0
    flat_count: int = 0
    total_volume: int | None = None
    average_volume: float | None = None
    top_gainer: str | None = None
    top_loser: str | None = None
    most_traded: str | None = None


class IndicatorContext(BaseModel):
    sector: SectorCode
    reference_date: date
    tickers: list[TickerIndicatorContext] = Field(default_factory=list)
    comparison: SectorComparisonContext = Field(default_factory=SectorComparisonContext)


class NewsContext(BaseModel):
    sector: SectorCode
    title: str
    url: str
    summary: str
    source: str
    published_at: datetime | None = None
    keywords: list[str] = Field(default_factory=list)


class AnalysisHypothesis(BaseModel):
    title: str
    description: str
    basis: list[str] = Field(default_factory=list)
    sources: list[SourceInfo] = Field(default_factory=list)


class HypothesisVerificationResult(BaseModel):
    hypothesis_title: str
    is_supported: bool
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[WarningMessage] = Field(default_factory=list)


class AgentState(BaseModel):
    user_message: str = ""
    sector: SectorCode | None = None
    session_id: str | None = None
    chat_history: list[ChatTurn] = Field(default_factory=list)
    request_type: RequestType | None = None
    indicator_context: IndicatorContext | None = None
    news_context: list[NewsContext] = Field(default_factory=list)
    hypotheses: list[AnalysisHypothesis] = Field(default_factory=list)
    verification_results: list[HypothesisVerificationResult] = Field(
        default_factory=list
    )
    beginner_summary: str | None = None
    key_evidence: list[KeyEvidence] = Field(default_factory=list)
    trend_label: str | None = None
    final_answer: str | None = None
    sources: list[SourceInfo] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    caution: str | None = None
    safety_notice: str | None = None
    draft_answer_is_safe: bool | None = None
    warnings: list[WarningMessage] = Field(default_factory=list)

    def to_graph_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
