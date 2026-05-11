from __future__ import annotations

import os
import re
from collections.abc import Mapping
from datetime import date, timedelta
from typing import Protocol

import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from performation_agent.state import SearchResult
from performation_agent.tools.cache import (
  DEFAULT_KOPIS_CACHE_TTL_SECONDS,
  cache_max_items,
  cache_ttl_seconds,
  get_or_set_cached,
)


KOPIS_PERFORMANCE_LIST_URL = "https://kopis.or.kr/openApi/restful/pblprfr"
KOPIS_PERFORMANCE_PAGE_URL = "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id={performance_id}"
DEFAULT_KOPIS_TIMEOUT_SECONDS = 10.0
DEFAULT_KOPIS_LOOKAHEAD_DAYS = 120
DEFAULT_KOPIS_ROWS = 10
MAX_KOPIS_LOOKAHEAD_DAYS = 365
MAX_KOPIS_WINDOW_DAYS = 31
MAX_KOPIS_RESPONSE_BYTES = 2_000_000
GENERIC_TERMS = ("콘서트", "공연", "페스티벌", "일정", "장소", "정보", "티켓", "예매", "준비물", "스탠딩")
KOPIS_SEARCH_ALIASES = {
  "랩비트": ("RAPBEAT", "RAP BEAT", "RAPBEAT FESTIVAL", "RAP BEAT FESTIVAL"),
}


class KopisProvider(Protocol):
  def search_performances(self, query: str) -> list[SearchResult]:
    ...


class KopisPerformanceProvider:
  def __init__(
    self,
    api_key: str,
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_KOPIS_TIMEOUT_SECONDS,
    lookahead_days: int = DEFAULT_KOPIS_LOOKAHEAD_DAYS,
    rows: int = DEFAULT_KOPIS_ROWS,
    start_date: date | None = None,
  ) -> None:
    self._api_key = api_key
    self._injected_client = client
    self._timeout_seconds = timeout_seconds
    self._lookahead_days = lookahead_days
    self._rows = rows
    self._start_date = start_date or date.today()

  def search_performances(self, query: str) -> list[SearchResult]:
    search_terms = _search_terms(query)
    if not search_terms:
      return []

    if self._injected_client is not None:
      return self._search_with_client(self._injected_client, query=query, search_terms=search_terms)
    with httpx.Client(timeout=self._timeout_seconds) as client:
      return self._search_with_client(client, query=query, search_terms=search_terms)

  def _search_with_client(self, client: httpx.Client, *, query: str, search_terms: list[str]) -> list[SearchResult]:
    results: list[SearchResult] = []
    for search_term in search_terms:
      for start, end in _date_windows(self._start_date, self._lookahead_days):
        response = self._get(client, search_term=search_term, start=start, end=end)
        response.raise_for_status()
        if len(response.content) > MAX_KOPIS_RESPONSE_BYTES:
          raise ValueError("KOPIS response is too large")
        results.extend(_normalize_kopis_results(response.text, query=query, match_query=search_term))
    return _dedupe_results(results)

  def _get(self, client: httpx.Client, *, search_term: str, start: date, end: date) -> httpx.Response:
    return client.get(
      KOPIS_PERFORMANCE_LIST_URL,
      params={
        "service": self._api_key,
        "stdate": _compact_date(start),
        "eddate": _compact_date(end),
        "cpage": 1,
        "rows": self._rows,
        "shprfnm": search_term,
      },
    )


def search_kopis_with_fallback(
  query: str,
  *,
  provider: KopisProvider | None = None,
  env: Mapping[str, str] | None = None,
) -> list[SearchResult]:
  selected_provider = provider or build_kopis_provider_from_env(env)
  if selected_provider is None:
    return []

  try:
    return get_or_set_cached(
      "kopis_search",
      _kopis_cache_key(selected_provider, query),
      ttl_seconds=cache_ttl_seconds(env, "PERFORMATION_KOPIS_CACHE_TTL_SECONDS", DEFAULT_KOPIS_CACHE_TTL_SECONDS),
      max_items=cache_max_items(env),
      factory=lambda: selected_provider.search_performances(query),
    )
  except (httpx.HTTPError, ET.ParseError, DefusedXmlException, ValueError):
    return []


def build_kopis_provider_from_env(env: Mapping[str, str] | None = None) -> KopisProvider | None:
  values = env or os.environ
  api_key = values.get("KOPIS_API_KEY", "").strip()
  if not api_key:
    return None
  return KopisPerformanceProvider(
    api_key,
    timeout_seconds=_float_env(values, "PERFORMATION_KOPIS_TIMEOUT_SECONDS", DEFAULT_KOPIS_TIMEOUT_SECONDS),
    lookahead_days=_int_env(
      values,
      "PERFORMATION_KOPIS_LOOKAHEAD_DAYS",
      DEFAULT_KOPIS_LOOKAHEAD_DAYS,
      minimum=1,
      maximum=MAX_KOPIS_LOOKAHEAD_DAYS,
    ),
    rows=_int_env(values, "PERFORMATION_KOPIS_ROWS", DEFAULT_KOPIS_ROWS, minimum=1, maximum=100),
  )


def _normalize_kopis_results(payload: str, *, query: str, match_query: str) -> list[SearchResult]:
  root = ET.fromstring(payload)
  results: list[SearchResult] = []
  for item in root.findall(".//db"):
    performance_id = _text(item, "mt20id")
    title = _text(item, "prfnm")
    if not performance_id or not title:
      continue
    if not _matches_query_title(title, match_query):
      continue
    results.append(
      {
        "title": f"{title} - KOPIS 공연 공식 데이터",
        "url": KOPIS_PERFORMANCE_PAGE_URL.format(performance_id=performance_id),
        "snippet": _snippet(item),
        "query": f"{query} KOPIS 공식 정보 일정 장소",
      }
    )
  return results


def _kopis_cache_key(provider: KopisProvider, query: str) -> dict[str, object]:
  return {
    "provider": f"{type(provider).__module__}.{type(provider).__qualname__}",
    "query": query,
    "start_date": getattr(provider, "_start_date", ""),
    "lookahead_days": getattr(provider, "_lookahead_days", ""),
    "rows": getattr(provider, "_rows", ""),
  }


def _snippet(item: ET.Element) -> str:
  start_text = _korean_date(_text(item, "prfpdfrom"))
  end_text = _korean_date(_text(item, "prfpdto"))
  period = _date_range(start_text, end_text)
  fields = [
    "공식 KOPIS 공연 데이터",
    f"공연명 {_text(item, 'prfnm')}",
    f"공연기간 {period}" if period else "",
    f"공연장소 {_text(item, 'fcltynm')}",
    f"지역 {_text(item, 'area')}",
    f"장르 {_text(item, 'genrenm')}",
    f"공연상태 {_text(item, 'prfstate')}",
  ]
  return ". ".join(field for field in fields if field and not field.endswith(" ")) + "."


def _date_windows(start: date, lookahead_days: int) -> list[tuple[date, date]]:
  final_day = start + timedelta(days=lookahead_days)
  windows: list[tuple[date, date]] = []
  current = start
  while current <= final_day:
    window_end = min(current + timedelta(days=MAX_KOPIS_WINDOW_DAYS - 1), final_day)
    windows.append((current, window_end))
    current = window_end + timedelta(days=1)
  return windows


def _search_term(query: str) -> str:
  normalized = query.strip()
  for term in GENERIC_TERMS:
    normalized = normalized.replace(term, " ")
  normalized = re.sub(r"\s+", " ", normalized).strip()
  return normalized if len(normalized) >= 2 else ""


def _search_terms(query: str) -> list[str]:
  search_term = _search_term(query)
  if not search_term:
    return []

  candidates = [search_term, *KOPIS_SEARCH_ALIASES.get(search_term.casefold(), ())]
  deduped: list[str] = []
  seen: set[str] = set()
  for candidate in candidates:
    normalized = candidate.strip()
    key = normalized.casefold()
    if not normalized or key in seen:
      continue
    deduped.append(normalized)
    seen.add(key)
  return deduped


def _matches_query_title(title: str, query: str) -> bool:
  search_term = _search_term(query)
  if not search_term:
    return False

  normalized_title = title.casefold()
  terms = [term for term in search_term.split() if term]
  return all(_term_in_title(term, normalized_title) for term in terms)


def _term_in_title(term: str, normalized_title: str) -> bool:
  normalized_term = term.casefold()
  if re.fullmatch(r"[a-z0-9]{2,3}", normalized_term):
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", normalized_title) is not None
  return normalized_term in normalized_title


def _text(item: ET.Element, tag: str) -> str:
  value = item.findtext(tag)
  return value.strip() if value else ""


def _compact_date(value: date) -> str:
  return value.strftime("%Y%m%d")


def _korean_date(value: str) -> str:
  match = re.fullmatch(r"(20\d{2})[.](\d{1,2})[.](\d{1,2})", value.strip())
  if not match:
    return value
  year, month, day = match.groups()
  return f"{year}년 {int(month)}월 {int(day)}일"


def _date_range(start_text: str, end_text: str) -> str:
  if not start_text:
    return end_text
  if not end_text or start_text == end_text:
    return start_text

  same_month_match = re.fullmatch(r"(20\d{2}년 \d{1,2}월 )(\d{1,2})일", start_text)
  end_same_month_match = re.fullmatch(r"(20\d{2}년 \d{1,2}월 )(\d{1,2})일", end_text)
  if same_month_match and end_same_month_match and same_month_match.group(1) == end_same_month_match.group(1):
    return f"{start_text}~{end_same_month_match.group(2)}일"
  return f"{start_text}~{end_text}"


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
  deduped: list[SearchResult] = []
  seen_urls: set[str] = set()
  for result in results:
    if result["url"] in seen_urls:
      continue
    deduped.append(result)
    seen_urls.add(result["url"])
  return deduped


def _float_env(values: Mapping[str, str], key: str, default: float) -> float:
  try:
    return float(values.get(key) or str(default))
  except ValueError:
    return default


def _int_env(
  values: Mapping[str, str],
  key: str,
  default: int,
  *,
  minimum: int,
  maximum: int | None = None,
) -> int:
  try:
    parsed = int(values.get(key) or str(default))
  except ValueError:
    parsed = default
  if maximum is not None:
    parsed = min(parsed, maximum)
  return max(parsed, minimum)
