from __future__ import annotations

from performation_agent.state import GuideState
from performation_domain import GuideResponse


def format_response(state: GuideState) -> GuideState:
  response = GuideResponse(
    input=state["query"],
    input_type=state["input_type"],
    venue=state.get("venue"),
    event_info=state.get("event_info"),
    event_candidates=state.get("event_candidates", []),
    summary=state.get("summary", []),
    checklist=state.get("checklist", []),
    transit_and_entry_tips=state.get("transit_and_entry_tips", []),
    official_check_required=state.get("official_check_required", []),
    sources=state.get("sources", []),
    confidence_notes=state.get("confidence_notes", []),
    fallback_used=state.get("fallback_used", False),
  )
  return {"response": response}
