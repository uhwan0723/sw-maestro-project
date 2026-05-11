from __future__ import annotations

import re
from datetime import date

from performation_agent.state import GuideState, SearchResult
from performation_agent.tools.source_classifier import classify_social_source
from performation_domain import ConfidenceLabel, EventCandidate, Source


CONCERT_INTENTS = {"venue_or_concert_name", "concert_or_event_name", "concert_detail_question"}
KOREAN_REGIONS = (
  "서울",
  "인천",
  "부산",
  "대구",
  "대전",
  "광주",
  "울산",
  "세종",
  "수원",
  "고양",
  "성남",
  "과천",
  "속초",
  "춘천",
  "강릉",
  "청주",
  "천안",
  "전주",
  "여수",
  "창원",
  "제주",
)
ENGLISH_REGIONS = {"SEOUL": "서울", "INCHEON": "인천", "BUSAN": "부산", "SOKCHO": "속초", "GOYANG": "고양"}
REGION_PATTERN = re.compile(r"(" + "|".join(KOREAN_REGIONS) + r")")
DATE_PATTERN = re.compile(
  r"(20\d{2}(?:년)?(?:\s*[0-9]{1,2}월)?(?:\s*[0-9]{1,2}일)?|[0-9]{1,2}월\s*[0-9]{1,2}일|[0-9]{1,2}월)"
)
DATE_RANGE_PATTERNS = (
  re.compile(r"(20\d{2}년\s*[0-9]{1,2}월\s*[0-9]{1,2}일)(?:\([^)]*\))?\s*~\s*([0-9]{1,2}일)"),
  re.compile(r"(20\d{2}년\s*[0-9]{1,2}월\s*[0-9]{1,2})\s*~\s*([0-9]{1,2}일)"),
)
REGION_DATE_PAIR_PATTERN = re.compile(r"(" + "|".join(KOREAN_REGIONS) + r")\s*\(([^)]*(?:월|일)[^)]*)\)")
YEAR_PATTERN = re.compile(r"(20\d{2})")
VENUE_PATTERN = re.compile(
  r"(?:공연\s*장소|공연장|장소|venue)(?:은|는|이|가)?[:：]?\s*([가-힣A-Za-z0-9][가-힣A-Za-z0-9\s&+\-\[\]]{1,40})",
  re.IGNORECASE,
)
STRICT_VENUE_PATTERN = re.compile(
  r"(?:공연\s*장소|공연장|장소|venue)(?:은|는|이|가|[:：])+\s*['\"]?([가-힣A-Za-z0-9][가-힣A-Za-z0-9\s&+\-\[\]]{1,40})",
  re.IGNORECASE,
)
CONFIDENCE_PRIORITY = {
  ConfidenceLabel.OFFICIAL_CONFIRMED: 4,
  ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED: 3,
  ConfidenceLabel.PUBLIC_REVIEW_REFERENCE: 2,
  ConfidenceLabel.UNCERTAIN: 1,
}
PUBLIC_SOURCE_HINTS = ("blog", "tistory", "namu.wiki", "kin.naver", "trip.com/blog", "후기", "리뷰")
OFFICIAL_SOURCE_HINTS = (
  "waterbombfestival.com",
  "rapbeatfestival.com",
  "ticketlink.co.kr",
  "nol.yanolja.com",
  "ticket.melon.com",
  "tickets.interpark.com",
  "instagram.com",
  "kopis.or.kr",
)


def infer_event_candidates(state: GuideState) -> GuideState:
  if state.get("venue") is not None:
    return {}
  if state.get("input_intent") not in CONCERT_INTENTS:
    return {}
  if not state.get("search_results"):
    return {}

  candidates_by_key: dict[tuple[str, str, str, str], EventCandidate] = {}
  for result in state.get("search_results", []):
    if not _candidate_evidence_query(result["query"]):
      continue
    for candidate in _candidates_from_result(state["query"], result):
      key = _candidate_key(candidate)
      existing_key = _existing_candidate_key(candidates_by_key, candidate)
      if existing_key is None:
        candidates_by_key[key] = candidate
      else:
        existing = candidates_by_key.pop(existing_key)
        _merge_candidate(existing, candidate)
        candidates_by_key[_candidate_key(existing)] = existing

  candidates = _filter_candidates(list(candidates_by_key.values()), state["query"])
  if not candidates:
    return {}

  return {
    "input_type": "event_candidates",
    "event_candidates": candidates[:6],
  }


def _candidates_from_result(query: str, result: SearchResult) -> list[EventCandidate]:
  evidence_text = " ".join((result["title"], result["snippet"]))
  source = _candidate_source(result)
  pair_candidates = [
    EventCandidate(
      name=_candidate_name(query, region),
      region=region,
      date_text=_pair_date_text(evidence_text, date_part),
      venue_name=_venue_name(result["title"], result["snippet"]) if source.source_type != ConfidenceLabel.PUBLIC_REVIEW_REFERENCE else "",
      confidence_label=source.source_type,
      sources=[source],
    )
    for region, date_part in REGION_DATE_PAIR_PATTERN.findall(evidence_text)
  ]
  if len(pair_candidates) >= 2:
    return pair_candidates

  region = _region(result["title"], result["snippet"])
  if not region:
    return []

  name = _candidate_name(query, region)
  date_text = _date_text(evidence_text)
  venue_name = _venue_name(result["title"], result["snippet"]) if source.source_type != ConfidenceLabel.PUBLIC_REVIEW_REFERENCE else ""
  return [
    EventCandidate(
      name=name,
      region=region,
      date_text=date_text,
      venue_name=venue_name,
      confidence_label=source.source_type,
      sources=[source],
    )
  ]


def _candidate_source(result: SearchResult) -> Source:
  confidence_label = _candidate_confidence(result)
  source = Source(
    title=result["title"],
    url=result["url"],
    source_type=confidence_label,
    used_for=[result["query"]],
  )
  return source


def _candidate_name(query: str, region: str) -> str:
  base_name = query.strip()
  for suffix in ("공연", "콘서트", "페스티벌", "일정", "장소"):
    base_name = base_name.replace(suffix, "")
  base_name = base_name.strip() or query.strip()
  if region in base_name:
    return base_name
  return f"{base_name} {region}".strip()


def _region(title: str, snippet: str) -> str:
  title_region = _first_match(REGION_PATTERN, title)
  if title_region:
    return title_region

  normalized_title = title.upper()
  for english_region, korean_region in ENGLISH_REGIONS.items():
    if english_region in normalized_title:
      return korean_region

  snippet_regions = list(dict.fromkeys(REGION_PATTERN.findall(snippet)))
  if len(snippet_regions) == 1:
    region = snippet_regions[0]
    if _region_looks_like_address_only(region, snippet):
      return ""
    return region
  return ""


def _candidate_key(candidate: EventCandidate) -> tuple[str, str, str, str]:
  return (candidate.name.casefold(), candidate.region, candidate.date_text, candidate.venue_name.casefold())


def _existing_candidate_key(
  candidates_by_key: dict[tuple[str, str, str, str], EventCandidate],
  candidate: EventCandidate,
) -> tuple[str, str, str, str] | None:
  key = _candidate_key(candidate)
  if key in candidates_by_key:
    return key

  for existing_key, existing in candidates_by_key.items():
    if existing_key[:2] != key[:2]:
      continue
    if not _dates_compatible(existing.date_text, candidate.date_text):
      continue
    if existing.venue_name and candidate.venue_name and existing.venue_name.casefold() != candidate.venue_name.casefold():
      continue
    if existing.venue_name and candidate.venue_name:
      return existing_key
    if not candidate.venue_name or not existing_key[3]:
      return existing_key
  return None


def _merge_candidate(existing: EventCandidate, candidate: EventCandidate) -> None:
  if CONFIDENCE_PRIORITY[candidate.confidence_label] > CONFIDENCE_PRIORITY[existing.confidence_label]:
    existing.confidence_label = candidate.confidence_label

  if _date_specificity(candidate.date_text) > _date_specificity(existing.date_text):
    existing.date_text = candidate.date_text
  if candidate.venue_name and not existing.venue_name:
    existing.venue_name = candidate.venue_name

  existing_urls = {source.url for source in existing.sources}
  for source in candidate.sources:
    if source.url not in existing_urls:
      existing.sources.append(source)
      existing_urls.add(source.url)


def _dates_compatible(left: str, right: str) -> bool:
  if not left or not right:
    return True
  left_year = YEAR_PATTERN.search(left)
  right_year = YEAR_PATTERN.search(right)
  if left_year and right_year:
    return left_year.group(1) == right_year.group(1)
  return left == right


def _date_specificity(value: str) -> int:
  if not value:
    return 0
  if "~" in value:
    return 4
  if "일" in value:
    return 3
  if "월" in value:
    return 2
  return 1


def _date_text(evidence_text: str) -> str:
  date_range_text = _date_range_text(evidence_text)
  if date_range_text:
    return date_range_text

  matches = [match.group(1).strip() for match in DATE_PATTERN.finditer(evidence_text)]
  if not matches:
    return ""
  matches_with_year = [match for match in matches if YEAR_PATTERN.search(match)]
  if matches_with_year:
    return max(matches_with_year, key=_date_specificity)
  return max(matches, key=_date_specificity)


def _date_range_text(evidence_text: str) -> str:
  for pattern in DATE_RANGE_PATTERNS:
    match = pattern.search(evidence_text)
    if match:
      return f"{match.group(1)}~{match.group(2)}"
  return ""


def _pair_date_text(evidence_text: str, date_part: str) -> str:
  year_match = YEAR_PATTERN.search(evidence_text)
  normalized_date_part = date_part.strip()
  if year_match and not YEAR_PATTERN.search(normalized_date_part):
    return f"{year_match.group(1)}년 {normalized_date_part}"
  return normalized_date_part


def _filter_candidates(candidates: list[EventCandidate], query: str) -> list[EventCandidate]:
  if not YEAR_PATTERN.search(query):
    candidates = _drop_past_candidates(candidates)
  candidates = _drop_undated_duplicates(candidates)
  return candidates[:6]


def _candidate_evidence_query(query: str) -> bool:
  return any(marker in query for marker in ("공식 정보", "공식 SNS 공지", "일정 장소"))


def _drop_past_candidates(candidates: list[EventCandidate]) -> list[EventCandidate]:
  today = date.today()
  return [candidate for candidate in candidates if not _candidate_is_past(candidate, today=today)]


def _drop_undated_duplicates(candidates: list[EventCandidate]) -> list[EventCandidate]:
  dated_keys = {(candidate.name.casefold(), candidate.region) for candidate in candidates if candidate.date_text}
  return [
    candidate
    for candidate in candidates
    if candidate.date_text or (candidate.name.casefold(), candidate.region) not in dated_keys
  ]


def _candidate_year(candidate: EventCandidate, *, current_year: int) -> int | None:
  year_match = YEAR_PATTERN.search(candidate.date_text)
  if year_match:
    return int(year_match.group(1))
  if candidate.date_text:
    return current_year
  return None


def _candidate_is_past(candidate: EventCandidate, *, today: date) -> bool:
  if not candidate.date_text:
    return False

  candidate_date = _candidate_start_date(candidate.date_text, today=today)
  if candidate_date is not None:
    return candidate_date < today

  candidate_year = _candidate_year(candidate, current_year=today.year)
  return candidate_year is not None and candidate_year < today.year


def _candidate_start_date(value: str, *, today: date) -> date | None:
  full_date_match = re.search(r"(20\d{2})년\s*([0-9]{1,2})월\s*([0-9]{1,2})(?:일)?", value)
  if full_date_match:
    return _safe_date(
      int(full_date_match.group(1)),
      int(full_date_match.group(2)),
      int(full_date_match.group(3)),
    )

  month_day_match = re.search(r"([0-9]{1,2})월\s*([0-9]{1,2})(?:일)?", value)
  if month_day_match:
    return _safe_date(today.year, int(month_day_match.group(1)), int(month_day_match.group(2)))

  return None


def _safe_date(year: int, month: int, day: int) -> date | None:
  try:
    return date(year, month, day)
  except ValueError:
    return None


def _venue_name(*evidence_fields: str) -> str:
  for evidence_text in evidence_fields:
    for pattern in (STRICT_VENUE_PATTERN, VENUE_PATTERN):
      venue_name = _first_clean_venue_name(pattern, evidence_text)
      if venue_name:
        return venue_name
  return ""


def _first_clean_venue_name(pattern: re.Pattern[str], evidence_text: str) -> str:
  for match in pattern.finditer(evidence_text):
    venue_name = _clean_venue_name(match.group(1))
    if venue_name:
      return venue_name
  return ""


def _clean_venue_name(value: str) -> str:
  cleaned = value.strip(" .,/|'\"")
  for marker in (
    "에서",
    "으로",
    " 올해는",
    " 올해",
    " 더 강력",
    " 사운드",
    " 물총",
    " 음악의",
    " 초호화",
    " 라인업",
    " 티켓",
    " 공식",
    " 공지",
    " 안내",
    " 일정",
    " 예매",
    " - ",
  ):
    cleaned = cleaned.split(marker, 1)[0]
  cleaned = cleaned.strip(" .,/|'\"")
  for region in KOREAN_REGIONS:
    cleaned = re.sub(rf"^{region}\s+(킨텍스\b)", r"\1", cleaned)
  if cleaned.startswith("안내"):
    return ""
  if any(term in cleaned for term in ("티켓", "티켓팅", "예매", "가격", "준비물", "라인업", "출연진", "추후 공개", "추후공지", "미정")):
    return ""
  if cleaned == "킨텍스 야외 글로벌":
    return "킨텍스 야외 글로벌 스테이지"
  return cleaned


def _candidate_confidence(result: SearchResult) -> ConfidenceLabel:
  social_label = classify_social_source(result)
  if social_label is not None:
    return social_label

  text = " ".join((result["title"], result["url"], result["snippet"])).casefold()
  if any(term in text for term in PUBLIC_SOURCE_HINTS):
    return ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  if "kopis.or.kr" in text or "kopis 공연" in text:
    return ConfidenceLabel.OFFICIAL_CONFIRMED
  if any(term in text for term in OFFICIAL_SOURCE_HINTS):
    return ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  if any(term in text for term in ("공식", "official", "ticket", "예매", "공지")):
    return ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  return ConfidenceLabel.UNCERTAIN


def _first_match(pattern: re.Pattern[str], text: str) -> str:
  match = pattern.search(text)
  return match.group(1).strip() if match else ""


def _region_looks_like_address_only(region: str, snippet: str) -> bool:
  compact_snippet = re.sub(r"\s+", "", snippet)
  if region == "고양" and any(term in compact_snippet for term in ("킨텍스", "일산", "경기고양", "고양시")):
    return True
  return False
