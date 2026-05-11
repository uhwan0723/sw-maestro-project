from __future__ import annotations

from performation_agent.state import GuideState
from performation_venue_data import get_default_repository


CONCERT_INTENTS = {"concert_or_event_name", "concert_detail_question"}


def infer_venue_from_search(state: GuideState) -> GuideState:
  if state.get("venue") is not None:
    return {}
  if state.get("input_intent") not in CONCERT_INTENTS:
    return {}

  repository = get_default_repository()
  matches_by_venue = {}
  for result in state.get("search_results", []):
    searchable_text = _searchable_evidence_text(result)
    for match in repository.find_matches_by_query(searchable_text):
      matches_by_venue.setdefault(match.venue.name, match)

  if len(matches_by_venue) != 1:
    return {}

  match = next(iter(matches_by_venue.values()))
  return {
    "venue": match.venue,
    "input_type": "concert_with_inferred_venue",
    "matched_venue_alias": match.alias,
    "venue_inference_source": "public_search",
  }


def _searchable_evidence_text(result) -> str:
  return " ".join((result["title"], result["snippet"]))
