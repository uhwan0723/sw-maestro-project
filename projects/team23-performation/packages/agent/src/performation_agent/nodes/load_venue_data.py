from __future__ import annotations

from performation_agent.state import GuideState
from performation_venue_data import get_default_repository


def load_venue_data(state: GuideState) -> GuideState:
  repository = get_default_repository()
  venue_match = repository.find_match_by_query(state["query"])
  venue = venue_match.venue if venue_match is not None else None

  return {
    "venue": venue,
    "input_type": _input_type_for(state, venue is not None),
    "matched_venue_alias": venue_match.alias if venue_match is not None else None,
  }


def _input_type_for(state: GuideState, has_venue: bool) -> str:
  if not has_venue:
    return "unsupported_or_ambiguous"

  input_intent = state.get("input_intent")
  if input_intent in {"concert_or_event_name", "concert_detail_question"}:
    return "concert_with_venue_hint"
  if input_intent == "detail_question":
    return "venue_with_detail_question"
  return "venue_name"
