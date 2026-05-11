from __future__ import annotations

import re
from datetime import date

from performation_agent.state import GuideState, SearchResult
from performation_agent.tools.source_classifier import classify_social_source
from performation_domain import ConfidenceLabel, EventInfo, Source


CONCERT_INTENTS = {"concert_or_event_name", "concert_detail_question"}
GENERIC_TERMS = ("콘서트", "공연", "페스티벌", "일정", "장소", "정보", "티켓", "예매")
DATE_PATTERNS = (
  re.compile(r"(20\d{2}[.]\s*[0-9]{1,2}[.]\s*[0-9]{1,2})"),
  re.compile(r"(20\d{2}년\s*[0-9]{1,2}월\s*[0-9]{1,2}일)"),
)
YEAR_PATTERN = re.compile(r"(20\d{2})")
TIME_PATTERN = re.compile(r"((?:[01]?[0-9]|2[0-3]):[0-5][0-9]|(?:[0-9]{1,2})\s*PM)", re.IGNORECASE)
SOURCE_PRIORITY = {
  ConfidenceLabel.OFFICIAL_CONFIRMED: 4,
  ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED: 3,
  ConfidenceLabel.UNCERTAIN: 2,
  ConfidenceLabel.PUBLIC_REVIEW_REFERENCE: 1,
}
PUBLIC_SOURCE_HINTS = ("blog", "tistory", "namu.wiki", "kin.naver", "후기", "리뷰")
OFFICIAL_SOURCE_HINTS = ("instagram.com", "yes24.com", "ticket.yes24.com", "kopis.or.kr")
TICKET_SOURCE_HINTS = ("stagepick.co.kr", "trip.com/events", "ticketlink.co.kr", "tickets.interpark.com")


def extract_event_info(state: GuideState) -> GuideState:
  if state.get("event_candidates"):
    return {}
  if state.get("venue") is None:
    return {}
  if state.get("input_intent") not in CONCERT_INTENTS:
    return {}

  query_terms = _query_terms(state["query"])
  scored_infos = [
    (score, event_info)
    for result in state.get("search_results", [])
    if _event_info_query(result["query"])
    for event_info in [_event_info_from_result(state, result, query_terms)]
    if event_info is not None
    for score in [_event_info_score(event_info)]
  ]
  if not scored_infos:
    return {}

  scored_infos.sort(key=lambda item: item[0], reverse=True)
  selected_info = scored_infos[0][1]
  for _, event_info in scored_infos[1:]:
    _merge_event_info(selected_info, event_info)
  return {"event_info": selected_info}


def _event_info_from_result(state: GuideState, result: SearchResult, query_terms: list[str]) -> EventInfo | None:
  evidence_text = " ".join((result["title"], result["snippet"]))
  if query_terms and not all(term.casefold() in evidence_text.casefold() for term in query_terms):
    return None

  date_text = _date_text(evidence_text)
  if not date_text:
    return None
  if not YEAR_PATTERN.search(state["query"]) and _event_date_is_past(date_text):
    return None

  venue_name = _venue_name(state, evidence_text)
  source_type = _source_type(result)
  return EventInfo(
    title=_event_title(state["query"], result["title"]),
    date_text=date_text,
    time_text=_time_text(evidence_text),
    venue_name=venue_name,
    confidence_label=source_type,
    sources=[
      Source(
        title=result["title"],
        url=result["url"],
        source_type=source_type,
        used_for=[result["query"]],
      )
    ],
  )


def _query_terms(query: str) -> list[str]:
  normalized_query = query
  for term in GENERIC_TERMS:
    normalized_query = normalized_query.replace(term, " ")
  return [term.strip() for term in normalized_query.split() if term.strip()]


def _event_info_query(query: str) -> bool:
  return any(marker in query for marker in ("공식 정보", "공식 SNS 공지", "일정 장소"))


def _event_info_score(event_info: EventInfo) -> tuple[int, int, int, int]:
  return (
    SOURCE_PRIORITY[event_info.confidence_label],
    1 if event_info.venue_name else 0,
    1 if event_info.time_text else 0,
    len(event_info.sources),
  )


def _merge_event_info(selected_info: EventInfo, event_info: EventInfo) -> None:
  if event_info.date_text != selected_info.date_text:
    return

  if SOURCE_PRIORITY[event_info.confidence_label] < SOURCE_PRIORITY[selected_info.confidence_label]:
    return

  if "..." in selected_info.title and "..." not in event_info.title:
    selected_info.title = event_info.title
  if not selected_info.venue_name and event_info.venue_name:
    selected_info.venue_name = event_info.venue_name
  if not selected_info.time_text and event_info.time_text and event_info.date_text == selected_info.date_text:
    selected_info.time_text = event_info.time_text

  seen_urls = {source.url for source in selected_info.sources}
  for source in event_info.sources:
    if source.url not in seen_urls:
      selected_info.sources.append(source)
      seen_urls.add(source.url)


def _date_text(evidence_text: str) -> str:
  for pattern in DATE_PATTERNS:
    match = pattern.search(evidence_text)
    if match:
      return _normalize_date(match.group(1))
  return ""


def _normalize_date(value: str) -> str:
  normalized = re.sub(r"\s+", " ", value).strip()
  if "년" in normalized:
    return normalized
  return re.sub(r"\s*[.]\s*", ".", normalized).strip(".")


def _event_date_is_past(value: str) -> bool:
  event_date = _event_date(value)
  return event_date is not None and event_date < date.today()


def _event_date(value: str) -> date | None:
  dotted_match = re.search(r"(20\d{2})[.]\s*([0-9]{1,2})[.]\s*([0-9]{1,2})", value)
  if dotted_match:
    return _safe_date(int(dotted_match.group(1)), int(dotted_match.group(2)), int(dotted_match.group(3)))

  korean_match = re.search(r"(20\d{2})년\s*([0-9]{1,2})월\s*([0-9]{1,2})일", value)
  if korean_match:
    return _safe_date(int(korean_match.group(1)), int(korean_match.group(2)), int(korean_match.group(3)))

  return None


def _safe_date(year: int, month: int, day: int) -> date | None:
  try:
    return date(year, month, day)
  except ValueError:
    return None


def _time_text(evidence_text: str) -> str:
  for match in TIME_PATTERN.finditer(evidence_text):
    prefix = evidence_text[max(0, match.start() - 20) : match.start()]
    if "오픈" in prefix:
      continue
    return re.sub(r"\s+", "", match.group(1).upper())
  return ""


def _venue_name(state: GuideState, evidence_text: str) -> str:
  venue = state.get("venue")
  if venue is None:
    return ""

  normalized_evidence = evidence_text.casefold().replace(" ", "")
  for alias in [venue.name, *venue.aliases]:
    if alias.casefold().replace(" ", "") in normalized_evidence:
      return venue.name
  return ""


def _event_title(query: str, title: str) -> str:
  cleaned_title = title.split(" - ", 1)[0].strip()
  cleaned_title = re.sub(r"^\[[^\]]+\]\s*", "", cleaned_title)
  cleaned_title = re.sub(r"\s*\(20\d{2}[^)]*\)", "", cleaned_title).strip()
  return cleaned_title or query


def _source_type(result: SearchResult) -> ConfidenceLabel:
  social_label = classify_social_source(result)
  if social_label is not None:
    return social_label

  text = " ".join((result["title"], result["url"], result["snippet"])).casefold()
  if any(term in text for term in PUBLIC_SOURCE_HINTS):
    return ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  if "kopis.or.kr" in text or "kopis 공연 공식 데이터" in text:
    return ConfidenceLabel.OFFICIAL_CONFIRMED
  if any(term in text for term in OFFICIAL_SOURCE_HINTS) and "공지" in text:
    return ConfidenceLabel.OFFICIAL_CONFIRMED
  if any(term in text for term in TICKET_SOURCE_HINTS):
    return ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  if any(term in text for term in ("공식", "official", "ticket", "예매", "공지")):
    return ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  return ConfidenceLabel.UNCERTAIN
