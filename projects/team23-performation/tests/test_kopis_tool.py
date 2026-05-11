from datetime import date

import httpx

from performation_agent.tools.cache import clear_agent_caches
from performation_agent.tools.kopis import (
  KOPIS_PERFORMANCE_LIST_URL,
  KOPIS_PERFORMANCE_PAGE_URL,
  KopisPerformanceProvider,
  build_kopis_provider_from_env,
  search_kopis_with_fallback,
)


def test_search_kopis_with_fallback_returns_empty_without_key(monkeypatch) -> None:
  monkeypatch.delenv("KOPIS_API_KEY", raising=False)

  assert search_kopis_with_fallback("EK 콘서트") == []


def test_build_kopis_provider_from_env_uses_api_key() -> None:
  provider = build_kopis_provider_from_env(
    {
      "KOPIS_API_KEY": "kopis-key",
      "PERFORMATION_KOPIS_LOOKAHEAD_DAYS": "31",
      "PERFORMATION_KOPIS_ROWS": "5",
    }
  )

  assert isinstance(provider, KopisPerformanceProvider)


def test_build_kopis_provider_from_env_caps_lookahead_days() -> None:
  provider = build_kopis_provider_from_env(
    {
      "KOPIS_API_KEY": "kopis-key",
      "PERFORMATION_KOPIS_LOOKAHEAD_DAYS": "9999",
    }
  )

  assert isinstance(provider, KopisPerformanceProvider)
  assert provider._lookahead_days == 365


def test_kopis_provider_normalizes_performance_list_xml() -> None:
  def handler(request: httpx.Request) -> httpx.Response:
    assert str(request.url).startswith(KOPIS_PERFORMANCE_LIST_URL)
    assert request.url.params["service"] == "kopis-test"
    assert request.url.params["shprfnm"] == "EK"
    assert request.url.params["stdate"] == "20260501"
    assert request.url.params["eddate"] == "20260531"
    assert request.url.params["rows"] == "2"
    return httpx.Response(
      200,
      text="""
      <dbs>
        <db>
          <mt20id>PF111111</mt20id>
          <prfnm>BELLEFORET WEEK: MY VOLUME [증평]</prfnm>
          <prfpdfrom>2026.06.06</prfpdfrom>
          <prfpdto>2026.06.06</prfpdto>
          <fcltynm>벨포레 리조트</fcltynm>
          <area>충청북도</area>
          <genrenm>대중음악</genrenm>
          <prfstate>공연예정</prfstate>
        </db>
        <db>
          <mt20id>PF999999</mt20id>
          <prfnm>EK 3rd Concert : You Good?</prfnm>
          <prfpdfrom>2026.05.10</prfpdfrom>
          <prfpdto>2026.05.10</prfpdto>
          <fcltynm>예스24라이브홀</fcltynm>
          <area>서울특별시</area>
          <genrenm>대중음악</genrenm>
          <prfstate>공연예정</prfstate>
        </db>
        <db>
          <mt20id>PF222222</mt20id>
          <prfnm>Unlock: NEKIRU New Member Debut</prfnm>
          <prfpdfrom>2026.05.29</prfpdfrom>
          <prfpdto>2026.05.29</prfpdto>
          <fcltynm>세티 라이브홀</fcltynm>
          <area>서울특별시</area>
          <genrenm>대중음악</genrenm>
          <prfstate>공연예정</prfstate>
        </db>
      </dbs>
      """,
    )

  with httpx.Client(transport=httpx.MockTransport(handler)) as client:
    provider = KopisPerformanceProvider(
      "kopis-test",
      client=client,
      start_date=date(2026, 5, 1),
      lookahead_days=30,
      rows=2,
    )
    results = provider.search_performances("EK 콘서트")

  assert results == [
    {
      "title": "EK 3rd Concert : You Good? - KOPIS 공연 공식 데이터",
      "url": KOPIS_PERFORMANCE_PAGE_URL.format(performance_id="PF999999"),
      "snippet": (
        "공식 KOPIS 공연 데이터. 공연명 EK 3rd Concert : You Good?. 공연기간 2026년 5월 10일. "
        "공연장소 예스24라이브홀. 지역 서울특별시. 장르 대중음악. 공연상태 공연예정."
      ),
      "query": "EK 콘서트 KOPIS 공식 정보 일정 장소",
    }
  ]


def test_kopis_provider_expands_known_korean_event_aliases() -> None:
  requested_terms: list[str] = []

  def handler(request: httpx.Request) -> httpx.Response:
    search_term = request.url.params["shprfnm"]
    requested_terms.append(search_term)
    if search_term != "RAPBEAT":
      return httpx.Response(200, text="<dbs></dbs>")
    return httpx.Response(
      200,
      text="""
      <dbs>
        <db>
          <mt20id>PF333333</mt20id>
          <prfnm>RAPBEAT 2026</prfnm>
          <prfpdfrom>2026.06.20</prfpdfrom>
          <prfpdto>2026.06.21</prfpdto>
          <fcltynm>문화비축기지</fcltynm>
          <area>서울특별시</area>
          <genrenm>대중음악</genrenm>
          <prfstate>공연예정</prfstate>
        </db>
      </dbs>
      """,
    )

  with httpx.Client(transport=httpx.MockTransport(handler)) as client:
    provider = KopisPerformanceProvider(
      "kopis-test",
      client=client,
      start_date=date(2026, 6, 1),
      lookahead_days=0,
      rows=2,
    )
    results = provider.search_performances("랩비트 페스티벌")

  assert requested_terms[:2] == ["랩비트", "RAPBEAT"]
  assert results == [
    {
      "title": "RAPBEAT 2026 - KOPIS 공연 공식 데이터",
      "url": KOPIS_PERFORMANCE_PAGE_URL.format(performance_id="PF333333"),
      "snippet": (
        "공식 KOPIS 공연 데이터. 공연명 RAPBEAT 2026. 공연기간 2026년 6월 20일~21일. "
        "공연장소 문화비축기지. 지역 서울특별시. 장르 대중음악. 공연상태 공연예정."
      ),
      "query": "랩비트 페스티벌 KOPIS 공식 정보 일정 장소",
    }
  ]


def test_search_kopis_with_fallback_handles_provider_errors() -> None:
  class FailingProvider:
    def search_performances(self, query: str):
      raise httpx.TimeoutException("timeout")

  assert search_kopis_with_fallback("워터밤", provider=FailingProvider()) == []


def test_search_kopis_with_fallback_caches_successful_results() -> None:
  clear_agent_caches()

  class CountingProvider:
    def __init__(self) -> None:
      self.calls = 0
      self._start_date = date(2026, 5, 1)
      self._lookahead_days = 120
      self._rows = 10

    def search_performances(self, query: str):
      self.calls += 1
      return [
        {
          "title": "워터밤 [서울] - KOPIS 공연 공식 데이터",
          "url": KOPIS_PERFORMANCE_PAGE_URL.format(performance_id="PF999998"),
          "snippet": f"{query} {self.calls}",
          "query": f"{query} KOPIS 공식 정보 일정 장소",
        }
      ]

  provider = CountingProvider()
  env = {"PERFORMATION_KOPIS_CACHE_TTL_SECONDS": "60"}

  first = search_kopis_with_fallback("워터밤", provider=provider, env=env)
  second = search_kopis_with_fallback("워터밤", provider=provider, env=env)

  assert first == second
  assert provider.calls == 1
