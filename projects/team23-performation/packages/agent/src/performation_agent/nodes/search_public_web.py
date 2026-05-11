from __future__ import annotations

from performation_agent.state import GuideState
from performation_agent.tools.search import search_with_fallback


def search_public_web(state: GuideState) -> GuideState:
  search_results = search_with_fallback(state.get("search_queries", []))
  return {
    "search_results": search_results,
    "fallback_used": not search_results,
  }
