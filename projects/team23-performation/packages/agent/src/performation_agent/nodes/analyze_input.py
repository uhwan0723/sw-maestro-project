from __future__ import annotations

from performation_agent.state import GuideState


DETAIL_KEYWORDS = ("준비물", "스탠딩", "입장", "물품보관", "교통", "주차", "동선")
CONCERT_KEYWORDS = ("콘서트", "공연", "투어", "팬미팅", "쇼케이스", "내한", "페스티벌", "뮤지컬")


def analyze_input(state: GuideState) -> GuideState:
  query = state["query"].strip()
  normalized_query = query.casefold()
  detail_keywords = [keyword for keyword in DETAIL_KEYWORDS if keyword.casefold() in normalized_query]
  concert_keywords = [keyword for keyword in CONCERT_KEYWORDS if keyword.casefold() in normalized_query]

  return {
    "query": query,
    "normalized_query": normalized_query,
    "input_intent": _input_intent(detail_keywords, concert_keywords),
    "detail_keywords": detail_keywords,
  }


def _input_intent(detail_keywords: list[str], concert_keywords: list[str]) -> str:
  if detail_keywords and concert_keywords:
    return "concert_detail_question"
  if detail_keywords:
    return "detail_question"
  if concert_keywords:
    return "concert_or_event_name"
  return "venue_or_concert_name"
