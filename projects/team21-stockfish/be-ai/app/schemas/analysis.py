from pydantic import BaseModel, Field

from app.models.enums import SectorCode
from app.schemas.common import SourceInfo, WarningMessage


class KeyEvidence(BaseModel):
    title: str
    description: str
    source: SourceInfo | None = None


class SectorAnalysisResponse(BaseModel):
    sector: SectorCode
    beginner_summary: str
    key_evidence: list[KeyEvidence]
    sources: list[SourceInfo] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    caution: str
    warnings: list[WarningMessage] = Field(default_factory=list)
