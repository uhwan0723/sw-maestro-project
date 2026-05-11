from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class ConfidenceLabel(str, Enum):
  OFFICIAL_CONFIRMED = "official_confirmed"
  PUBLIC_REVIEW_REFERENCE = "public_review_reference"
  LATEST_OFFICIAL_CHECK_REQUIRED = "latest_official_check_required"
  UNCERTAIN = "uncertain"


class Source(BaseModel):
  title: str
  url: str
  source_type: ConfidenceLabel
  used_for: list[str] = Field(default_factory=list)


class VenueInfo(BaseModel):
  name: str
  aliases: list[str] = Field(default_factory=list)
  address: str = ""
  nearest_station: str = ""
  transit_notes: list[str] = Field(default_factory=list)
  entry_notes: list[str] = Field(default_factory=list)
  locker_notes: list[str] = Field(default_factory=list)
  convenience_notes: list[str] = Field(default_factory=list)
  event_check_items: list[str] = Field(default_factory=list)
  sources: list[Source] = Field(default_factory=list)


class EventCandidate(BaseModel):
  name: str
  region: str = ""
  date_text: str = ""
  venue_name: str = ""
  confidence_label: ConfidenceLabel = ConfidenceLabel.UNCERTAIN
  sources: list[Source] = Field(default_factory=list)


class EventInfo(BaseModel):
  title: str = ""
  date_text: str = ""
  time_text: str = ""
  venue_name: str = ""
  confidence_label: ConfidenceLabel = ConfidenceLabel.UNCERTAIN
  sources: list[Source] = Field(default_factory=list)


class ErrorResponse(BaseModel):
  status: str = "error"
  error_message: str
  detail: str | None = None


class GuideRequest(BaseModel):
  query: Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
  ]


class GuideResponse(BaseModel):
  input: str
  input_type: str
  venue: VenueInfo | None = None
  event_info: EventInfo | None = None
  event_candidates: list[EventCandidate] = Field(default_factory=list)
  summary: list[str] = Field(default_factory=list)
  checklist: list[str] = Field(default_factory=list)
  transit_and_entry_tips: list[str] = Field(default_factory=list)
  official_check_required: list[str] = Field(default_factory=list)
  sources: list[Source] = Field(default_factory=list)
  confidence_notes: list[str] = Field(default_factory=list)
  fallback_used: bool = False
