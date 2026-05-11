from __future__ import annotations

from collections.abc import Mapping

from performation_agent.state import GuideState
from performation_agent.tools.kopis import KopisProvider, search_kopis_with_fallback


KOPIS_SEARCH_INTENTS = {"venue_or_concert_name", "concert_or_event_name", "concert_detail_question"}


def search_kopis_official(
  state: GuideState,
  *,
  provider: KopisProvider | None = None,
  env: Mapping[str, str] | None = None,
) -> GuideState:
  if state.get("input_intent") not in KOPIS_SEARCH_INTENTS:
    return {}
  if state.get("input_intent") == "venue_or_concert_name" and state.get("venue") is not None:
    return {}

  kopis_results = search_kopis_with_fallback(state["query"], provider=provider, env=env)
  if not kopis_results:
    return {}

  combined_results = [*kopis_results, *state.get("search_results", [])]
  return {
    "search_results": combined_results,
    "fallback_used": False,
  }
