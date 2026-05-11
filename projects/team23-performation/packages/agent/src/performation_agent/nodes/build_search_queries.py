from __future__ import annotations

from datetime import date

from performation_agent.state import GuideState, SearchQuery


QUERY_PURPOSES = (
  ("공식 정보", "official"),
  ("공식 SNS 공지", "official_sns"),
  ("입장 정보", "entry"),
  ("교통 정보", "transit"),
  ("물품보관", "locker"),
  ("준비물 팁", "preparation"),
  ("관람 후기 꿀팁", "review_tips"),
  ("입장 대기 스탠딩 후기", "review_entry"),
  ("물품보관 퇴장 교통 후기", "review_logistics"),
)
CANDIDATE_QUERY_INTENTS = {"venue_or_concert_name", "concert_or_event_name", "concert_detail_question"}


def build_search_queries(state: GuideState) -> GuideState:
  base_query = _build_base_query(state)
  query_purposes = _query_purposes(state)
  queries: list[SearchQuery] = [
    {"query": f"{base_query} {query_suffix}", "purpose": purpose}
    for query_suffix, purpose in query_purposes
  ]

  return {"search_queries": queries}


def _query_purposes(state: GuideState) -> tuple[tuple[str, str], ...]:
  if state.get("venue") is None and state.get("input_intent") in CANDIDATE_QUERY_INTENTS:
    candidate_query_purposes = (
      (f"{date.today().year} 일정 장소", "event_candidates"),
      (f"{date.today().year} 서울 부산 일정 장소", "event_candidates"),
    )
    return (QUERY_PURPOSES[0], *candidate_query_purposes, *QUERY_PURPOSES[1:])
  return QUERY_PURPOSES


def _build_base_query(state: GuideState) -> str:
  venue = state.get("venue")
  original_query = state["query"]
  if venue is None:
    return original_query

  query_parts = [venue.name]
  if original_query.casefold() != venue.name.casefold():
    query_parts.append(original_query)

  return " ".join(query_parts)
