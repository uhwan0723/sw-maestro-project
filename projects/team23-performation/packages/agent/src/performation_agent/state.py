from __future__ import annotations

from typing import TypedDict

from performation_domain import EventCandidate, EventInfo, GuideResponse, Source, VenueInfo


class SearchQuery(TypedDict):
  query: str
  purpose: str


class SearchResult(TypedDict):
  title: str
  url: str
  snippet: str
  query: str


class ClassifiedSource(TypedDict):
  source: Source
  reason: str


class GuideDraft(TypedDict):
  summary: list[str]
  checklist: list[str]
  transit_and_entry_tips: list[str]
  official_check_required: list[str]


class GuideState(TypedDict, total=False):
  query: str
  normalized_query: str
  input_intent: str
  input_type: str
  detail_keywords: list[str]
  matched_venue_alias: str | None
  venue_inference_source: str | None
  venue: VenueInfo | None
  event_info: EventInfo | None
  event_candidates: list[EventCandidate]
  search_queries: list[SearchQuery]
  search_results: list[SearchResult]
  classified_sources: list[ClassifiedSource]
  summary: list[str]
  checklist: list[str]
  transit_and_entry_tips: list[str]
  official_check_required: list[str]
  sources: list[Source]
  confidence_notes: list[str]
  fallback_used: bool
  llm_used: bool
  response: GuideResponse
