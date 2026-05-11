import importlib
from datetime import date

from performation_agent import generate_visit_guide
from performation_agent.nodes.analyze_input import analyze_input
from performation_agent.nodes.assign_confidence import assign_confidence
from performation_agent.nodes.build_search_queries import build_search_queries
from performation_agent.nodes.classify_sources import classify_sources
from performation_agent.nodes.extract_event_info import extract_event_info
from performation_agent.nodes.infer_event_candidates import infer_event_candidates
from performation_agent.nodes.infer_venue_from_search import infer_venue_from_search
from performation_agent.nodes.load_venue_data import load_venue_data
from performation_agent.nodes.search_kopis_official import search_kopis_official
from performation_agent.nodes.summarize_information import summarize_information
from performation_agent.workflow import NODE_SEQUENCE
from performation_domain import ConfidenceLabel, EventCandidate, EventInfo, VenueInfo


def test_workflow_has_expected_node_sequence() -> None:
  assert NODE_SEQUENCE == (
    "analyze_input",
    "load_venue_data",
    "build_search_queries",
    "search_public_web",
    "search_kopis_official",
    "infer_venue_from_search",
    "infer_event_candidates",
    "extract_event_info",
    "classify_sources",
    "summarize_information",
    "assign_confidence",
    "format_response",
  )


def test_search_kopis_official_merges_official_results() -> None:
  class FakeKopisProvider:
    def search_performances(self, query: str):
      return [
        {
          "title": "EK 3rd Concert : You Good? - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999999",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 5월 10일. 공연장소 예스24라이브홀. 지역 서울특별시.",
          "query": f"{query} KOPIS 공식 정보 일정 장소",
        }
      ]

  result = search_kopis_official(
    {
      "query": "EK 콘서트",
      "input_intent": "concert_or_event_name",
      "search_results": [
        {
          "title": "기존 공개 검색 결과",
          "url": "https://example.com/result",
          "snippet": "공개 검색 결과",
          "query": "EK 콘서트 공식 정보",
        }
      ],
      "fallback_used": False,
    },
    provider=FakeKopisProvider(),
  )

  assert len(result["search_results"]) == 2
  assert result["search_results"][0]["title"].endswith("KOPIS 공연 공식 데이터")
  assert result["fallback_used"] is False


def test_search_kopis_official_skips_supported_venue_name() -> None:
  class FailingKopisProvider:
    def search_performances(self, query: str):
      raise AssertionError("KOPIS should not run for pure supported venue names")

  result = search_kopis_official(
    {
      "query": "예스24라이브홀",
      "input_intent": "venue_or_concert_name",
      "venue": VenueInfo(name="YES24 Live Hall"),
    },
    provider=FailingKopisProvider(),
  )

  assert result == {}


def test_kopis_source_is_classified_as_official() -> None:
  result = classify_sources(
    {
      "search_results": [
        {
          "title": "EK 3rd Concert : You Good? - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999999",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 5월 10일. 공연장소 예스24라이브홀.",
          "query": "EK 콘서트 KOPIS 공식 정보 일정 장소",
        }
      ]
    }
  )

  assert result["sources"][0].source_type == ConfidenceLabel.OFFICIAL_CONFIRMED


def test_kopis_candidate_uses_official_confidence() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 서울 - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999999",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 7월 24일~26일. 공연장소 킨텍스 야외 글로벌 스테이지. 지역 서울특별시.",
          "query": "워터밤 KOPIS 공식 정보 일정 장소",
        }
      ],
    }
  )

  assert result["event_candidates"][0].confidence_label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert result["event_candidates"][0].venue_name == "킨텍스 야외 글로벌 스테이지"


def test_kopis_candidates_include_non_mvp_regional_options() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 [서울] - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF284703",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 7월 24일~26일. 공연장소 킨텍스. 지역 경기도.",
          "query": "워터밤 KOPIS 공식 정보 일정 장소",
        },
        {
          "title": "워터밤 [속초] - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF284704",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 8월 22일. 공연장소 한화리조트 [설악 쏘라노]. 지역 강원특별자치도.",
          "query": "워터밤 KOPIS 공식 정보 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert [(candidate.region, candidate.venue_name) for candidate in candidates] == [
    ("서울", "킨텍스"),
    ("속초", "한화리조트 [설악 쏘라노]"),
  ]
  assert all(candidate.confidence_label == ConfidenceLabel.OFFICIAL_CONFIRMED for candidate in candidates)


def test_kopis_event_info_uses_official_confidence() -> None:
  result = extract_event_info(
    {
      "query": "EK 콘서트",
      "input_intent": "concert_or_event_name",
      "venue": VenueInfo(name="YES24 Live Hall", aliases=["예스24라이브홀"]),
      "search_results": [
        {
          "title": "EK 3rd Concert : You Good? - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999999",
          "snippet": "공식 KOPIS 공연 데이터. 공연기간 2026년 5월 10일. 공연장소 예스24라이브홀. 지역 서울특별시.",
          "query": "EK 콘서트 KOPIS 공식 정보 일정 장소",
        }
      ],
    }
  )

  assert result["event_info"].confidence_label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert result["event_info"].date_text == "2026년 5월 10일"


def test_supported_venue_returns_fallback_guide() -> None:
  guide = generate_visit_guide("KSPO DOME 콘서트 준비물")

  assert guide.input_type == "concert_with_venue_hint"
  assert guide.venue is not None
  assert guide.venue.name == "KSPO DOME"
  assert guide.fallback_used is True
  assert guide.sources
  assert "물품보관 운영 여부 확인" in guide.checklist


def test_unsupported_venue_is_clear_about_mvp_scope() -> None:
  guide = generate_visit_guide("처음 보는 소극장")

  assert guide.input_type == "unsupported_or_ambiguous"
  assert guide.venue is None
  assert guide.fallback_used is True
  assert any("MVP" in item for item in guide.summary)


def test_supported_venue_examples_keep_existing_fallback_behavior() -> None:
  examples = [
    ("KSPO DOME 콘서트 준비물", "KSPO DOME"),
    ("블루스퀘어", "Blue Square"),
    ("예스24라이브홀 스탠딩", "YES24 Live Hall"),
  ]

  for query, venue_name in examples:
    guide = generate_visit_guide(query)
    assert guide.venue is not None
    assert guide.venue.name == venue_name
    assert guide.fallback_used is True
    assert guide.checklist


def test_concert_query_with_venue_hint_infers_supported_venue() -> None:
  guide = generate_visit_guide("아이유 콘서트 KSPO")

  assert guide.input_type == "concert_with_venue_hint"
  assert guide.venue is not None
  assert guide.venue.name == "KSPO DOME"
  assert guide.fallback_used is True
  assert guide.checklist


def test_concert_detail_query_with_venue_hint_keeps_concert_input_type() -> None:
  guide = generate_visit_guide("아이유 콘서트 KSPO 스탠딩")

  assert guide.input_type == "concert_with_venue_hint"
  assert guide.venue is not None
  assert guide.venue.name == "KSPO DOME"


def test_venue_alias_with_live_word_stays_venue_name() -> None:
  guide = generate_visit_guide("예스24라이브홀")

  assert guide.input_type == "venue_name"
  assert guide.venue is not None
  assert guide.venue.name == "YES24 Live Hall"


def test_concert_query_without_venue_hint_stays_ambiguous() -> None:
  guide = generate_visit_guide("아이유 콘서트 티켓팅")

  assert guide.input_type == "unsupported_or_ambiguous"
  assert guide.venue is None
  assert any("공연장명" in item for item in guide.summary)


def test_infer_venue_from_search_sets_single_supported_venue() -> None:
  result = infer_venue_from_search(
    {
      "query": "아이유 콘서트",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "아이유 콘서트 KSPO DOME 공연 안내",
          "url": "https://example.com/iu-kspo",
          "snippet": "서울 KSPO DOME에서 열리는 공연 정보입니다.",
          "query": "아이유 콘서트 공식 정보",
        }
      ],
    }
  )

  assert result["input_type"] == "concert_with_inferred_venue"
  assert result["venue"].name == "KSPO DOME"
  assert result["matched_venue_alias"] == "KSPO DOME"
  assert result["venue_inference_source"] == "public_search"


def test_infer_venue_from_search_does_not_guess_multiple_supported_venues() -> None:
  result = infer_venue_from_search(
    {
      "query": "아이유 콘서트",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "아이유 콘서트 KSPO DOME",
          "url": "https://example.com/iu-kspo",
          "snippet": "KSPO DOME 공연 정보",
          "query": "아이유 콘서트 공식 정보",
        },
        {
          "title": "아이유 콘서트 Blue Square",
          "url": "https://example.com/iu-blue-square",
          "snippet": "Blue Square 공연 정보",
          "query": "아이유 콘서트 공식 정보",
        },
      ],
    }
  )

  assert result == {}


def test_infer_venue_from_search_ignores_url_only_matches() -> None:
  result = infer_venue_from_search(
    {
      "query": "랩비트 공연",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "랩비트 공연 정보",
          "url": "https://example.com/kspo-dome-archive",
          "snippet": "공연 일정과 티켓 안내를 확인하세요.",
          "query": "랩비트 공연 공식 정보",
        }
      ],
    }
  )

  assert result == {}


def test_infer_event_candidates_returns_multiple_regional_options() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 서울 2026 일정 장소: 서울월드컵경기장",
          "url": "https://example.com/waterbomb-seoul",
          "snippet": "공식 예매 공지에서 서울 공연 일정과 장소를 확인하세요.",
          "query": "워터밤 2026 일정 장소",
        },
        {
          "title": "워터밤 인천 2026 일정 장소: 송도",
          "url": "https://example.com/waterbomb-incheon",
          "snippet": "인천 공연 일정은 공식 공지 기준으로 확인이 필요합니다.",
          "query": "워터밤 2026 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert result["input_type"] == "event_candidates"
  assert [candidate.region for candidate in candidates] == ["서울", "인천"]
  assert candidates[0].name == "워터밤 서울"
  assert candidates[0].venue_name == "서울월드컵경기장"
  assert candidates[0].sources


def test_infer_event_candidates_detects_full_dates_and_sejong() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 세종 2026년 7월 10일 장소: 세종호수공원",
          "url": "https://example.com/waterbomb-sejong",
          "snippet": "세종 공연 일정과 장소 안내",
          "query": "워터밤 일정 장소",
        },
        {
          "title": "워터밤 서울 8월 3일 장소: 한강공원",
          "url": "https://example.com/waterbomb-seoul",
          "snippet": "서울 공연 일정과 장소 안내",
          "query": "워터밤 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].region == "세종"
  assert candidates[0].date_text == "2026년 7월 10일"
  assert candidates[1].date_text == "8월 3일"


def test_infer_event_candidates_keeps_same_region_date_venue_conflicts_separate() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 서울 2026년 7월 10일 장소: 킨텍스",
          "url": "https://example.com/waterbomb-seoul-k",
          "snippet": "일정과 장소 안내",
          "query": "워터밤 일정 장소",
        },
        {
          "title": "워터밤 서울 2026년 7월 10일 장소: 킨텍스 공식 공지",
          "url": "https://example.com/waterbomb-seoul-k",
          "snippet": "공식 공지 기준으로 최신 확인이 필요합니다.",
          "query": "워터밤 공식 정보",
        },
        {
          "title": "워터밤 서울 2026년 7월 10일 장소: 올림픽공원",
          "url": "https://example.com/waterbomb-seoul-o",
          "snippet": "다른 장소 후보 안내",
          "query": "워터밤 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert [candidate.venue_name for candidate in candidates] == ["킨텍스", "올림픽공원"]
  assert candidates[0].confidence_label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert len(candidates[0].sources) == 1
  assert [source.url for source in candidates[0].sources] == ["https://example.com/waterbomb-seoul-k"]
  assert [source.url for source in candidates[1].sources] == ["https://example.com/waterbomb-seoul-o"]


def test_infer_event_candidates_merges_same_venue_year_and_specific_date() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"워터밤 서울 {current_year} 장소: 킨텍스",
          "url": "https://example.com/waterbomb-summary",
          "snippet": f"{current_year}년 개최 예정",
          "query": f"워터밤 {current_year} 일정 장소",
        },
        {
          "title": "워터밤 [서울] - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999998",
          "snippet": f"공식 KOPIS 공연 데이터. 공연기간 {current_year}년 7월 24일~26일. 공연장소 킨텍스.",
          "query": "워터밤 KOPIS 공식 정보 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert len(candidates) == 1
  assert candidates[0].date_text == f"{current_year}년 7월 24일~26일"
  assert candidates[0].confidence_label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert len(candidates[0].sources) == 2


def test_infer_event_candidates_trims_ticket_suffix_before_merging_venue() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "서울재즈페스티벌",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "제18회 서울재즈페스티벌 - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF999997",
          "snippet": f"공식 KOPIS 공연 데이터. 공연기간 {current_year}년 5월 22일~24일. 공연장소 올림픽공원.",
          "query": "서울재즈페스티벌 KOPIS 공식 정보 일정 장소",
        },
        {
          "title": f"서울재즈페스티벌 {current_year} 장소: 올림픽공원 티켓",
          "url": "https://example.com/seoul-jazz-ticket",
          "snippet": f"{current_year}년 5월 22일 티켓 안내",
          "query": f"서울재즈페스티벌 {current_year} 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert len(candidates) == 1
  assert candidates[0].venue_name == "올림픽공원"
  assert candidates[0].date_text == f"{current_year}년 5월 22일~24일"
  assert len(candidates[0].sources) == 2


def test_infer_event_candidates_merges_empty_venue_into_named_candidate() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "랩비트 페스티벌",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"랩비트 서울 {current_year} 개최 확정",
          "url": "https://example.com/rapbeat-seoul-summary",
          "snippet": f"{current_year}년 서울 공연 일정 안내",
          "query": "랩비트 페스티벌 공식 정보",
        },
        {
          "title": f"RAPBEAT {current_year} 개최 확정",
          "url": "https://example.com/rapbeat-seoul-venue",
          "snippet": f"일정 {current_year}년 6월 20일 장소 서울 마포 문화비축기지 초호화 라인업 - 지코",
          "query": "랩비트 페스티벌 일정 장소",
        },
        {
          "title": f"랩비트 부산 {current_year} 장소: 부산항",
          "url": "https://example.com/rapbeat-busan",
          "snippet": "부산 공연 일정 안내",
          "query": "랩비트 페스티벌 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  seoul_candidates = [candidate for candidate in candidates if candidate.region == "서울"]
  assert len(seoul_candidates) == 1
  assert seoul_candidates[0].venue_name == "서울 마포 문화비축기지"
  assert len(seoul_candidates[0].sources) == 2


def test_infer_event_candidates_prefers_current_candidates_for_yearless_query() -> None:
  current_year = date.today().year
  last_year = current_year - 1
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"워터밤 서울 {last_year} 장소는 티켓팅",
          "url": "https://blog.example.com/waterbomb-old",
          "snippet": "지난 후기",
          "query": "워터밤 후기",
        },
        {
          "title": f"워터밤 서울 {current_year} 개최 확정",
          "url": "https://www.waterbombfestival.com/post/current",
          "snippet": f"워터밤 서울은 {current_year}년 7월 24일 장소는 킨텍스 야외 글로벌 스테이지에서 진행됩니다.",
          "query": "워터밤 공식 정보",
        },
        {
          "title": f"워터밤 부산 {current_year}",
          "url": "https://shop.waterbombfestival.com/ko/products/waterbomb-busan",
          "snippet": "장소: 부산 엑스 더 스카이",
          "query": "워터밤 일정 장소",
        },
      ],
    }
  )

  candidates = result["event_candidates"]
  assert [candidate.region for candidate in candidates] == ["서울", "부산"]
  assert candidates[0].date_text == f"{current_year}년 7월 24일"
  assert candidates[0].venue_name == "킨텍스 야외 글로벌 스테이지"
  assert candidates[1].venue_name == "부산 엑스 더 스카이"
  assert all(str(last_year) not in candidate.date_text for candidate in candidates)


def test_infer_event_candidates_drops_past_only_candidates_for_yearless_query() -> None:
  last_year = date.today().year - 1
  result = infer_event_candidates(
    {
      "query": "싸이 흠뻑쇼",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"싸이 흠뻑쇼 인천 {last_year} 공식 일정",
          "url": "https://www.instagram.com/psy_oppa/p/example/",
          "snippet": f"{last_year}년 인천 공연 공식 공지",
          "query": "싸이 흠뻑쇼 공식 정보",
        },
        {
          "title": f"싸이 흠뻑쇼 대전 {last_year} 공식 일정",
          "url": "https://www.instagram.com/psy_oppa/p/example2/",
          "snippet": f"{last_year}년 대전 공연 공식 공지",
          "query": "싸이 흠뻑쇼 공식 SNS 공지",
        },
      ],
    }
  )

  assert result == {}


def test_infer_event_candidates_uses_title_region_before_address_region() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "TOUR SEOUL | WATERBOMB KOREA",
          "url": "https://www.waterbombfestival.com/tour-seoul",
          "snippet": "킨텍스 야외 글로벌 스테이지 경기 고양시 일산서구 킨텍스로",
          "query": "워터밤 공식 정보",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].region == "서울"
  assert candidates[0].name == "워터밤 서울"


def test_infer_event_candidates_does_not_use_kintex_address_as_region_without_event_region() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "WATERBOMB KOREA 공식 장소 안내",
          "url": "https://www.waterbombfestival.com/tour-seoul",
          "snippet": "공연 장소: 고양 킨텍스 야외 글로벌 스테이지 올해는 더 강력한 사운드로 진행. 경기 고양시 일산서구 킨텍스로",
          "query": "워터밤 공식 정보",
        }
      ],
    }
  )

  assert result == {}


def test_infer_event_candidates_trims_kintex_marketing_copy() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"워터밤 서울 {current_year} 장소: 고양 킨텍스 야외 글로벌 스테이지 올해는 더 강력한 사운드",
          "url": "https://www.waterbombfestival.com/tour-seoul",
          "snippet": f"공식 공지. {current_year}년 7월 24일 개최",
          "query": "워터밤 공식 정보",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].region == "서울"
  assert candidates[0].venue_name == "킨텍스 야외 글로벌 스테이지"


def test_infer_event_candidates_does_not_trust_public_review_venue() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 부산 2026 티켓 예매 정보",
          "url": "https://example.com/blog/waterbomb-busan",
          "snippet": "장소: 부산 엑스 더 스카이",
          "query": "워터밤 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].confidence_label == ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  assert candidates[0].venue_name == ""


def test_infer_event_candidates_skips_venue_heading_noise() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "개최 장소 안내 워터밤 서울 2026의 개최 장소는 '킨텍스 야외 글로벌 스테이지'",
          "url": "https://www.instagram.com/p/example/",
          "snippet": "공식 공지",
          "query": "워터밤 2026 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].venue_name == "킨텍스 야외 글로벌 스테이지"


def test_infer_event_candidates_normalizes_truncated_kintex_stage() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 서울 2026 개최 장소는 '킨텍스 야외 글로벌 ...",
          "url": "https://www.instagram.com/p/example/",
          "snippet": "공식 공지",
          "query": "워터밤 2026 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].venue_name == "킨텍스 야외 글로벌 스테이지"


def test_infer_event_candidates_treats_tba_as_missing_venue() -> None:
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "워터밤 부산 2026 장소: 추후 공개",
          "url": "https://www.waterbombfestival.com/post/current",
          "snippet": "공식 공지",
          "query": "워터밤 2026 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].venue_name == ""


def test_infer_event_candidates_splits_region_date_pairs_from_one_source() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"'워터밤 {current_year}' 서울·부산 개최 확정",
          "url": "https://www.waterbombfestival.com/post/current",
          "snippet": f"워터밤이 {current_year}년 여름, 서울(7월 24~26일)과 부산(8월 7~9일)에서의 국내 개최를 확정했다.",
          "query": f"워터밤 {current_year} 서울 부산 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert [(candidate.region, candidate.date_text) for candidate in candidates] == [
    ("서울", f"{current_year}년 7월 24~26일"),
    ("부산", f"{current_year}년 8월 7~9일"),
  ]


def test_extract_event_info_for_single_inferred_concert() -> None:
  result = extract_event_info(
    {
      "query": "EK 콘서트",
      "input_intent": "concert_or_event_name",
      "input_type": "concert_with_inferred_venue",
      "venue": VenueInfo(name="YES24 Live Hall", aliases=["YES24 LIVE HALL", "예스24라이브홀"]),
      "search_results": [
        {
          "title": "[EK 단독 콘서트 공지] EK 3rd concert '26 : you good ? EK ... - Instagram",
          "url": "https://www.instagram.com/p/example/",
          "snippet": "날짜 : 2026.05.10 (일) 장소 : YES24 LIVE HALL 티켓 오픈 : 2026.03.25 19:00 (수)",
          "query": "EK 콘서트 공식 정보",
        },
        {
          "title": "EK 3rd Concert : You Good? (2026.05.10) - StagePick",
          "url": "https://www.stagepick.co.kr/performances/detail/212761",
          "snippet": "공연 시간: 2026. 05. 10 18:00. 공연 장소. 예스24라이브홀.",
          "query": "EK 콘서트 2026 일정 장소",
        },
      ],
    }
  )

  event_info = result["event_info"]
  assert event_info.title == "EK 3rd Concert : You Good?"
  assert event_info.date_text == "2026.05.10"
  assert event_info.time_text == "18:00"
  assert event_info.venue_name == "YES24 Live Hall"
  assert event_info.confidence_label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert len(event_info.sources) == 2


def test_extract_event_info_keeps_matching_date_sources_only() -> None:
  result = extract_event_info(
    {
      "query": "EK 콘서트",
      "input_intent": "concert_or_event_name",
      "input_type": "concert_with_inferred_venue",
      "venue": VenueInfo(name="YES24 Live Hall", aliases=["YES24 LIVE HALL"]),
      "search_results": [
        {
          "title": "[EK 단독 콘서트 공지] EK 3rd concert '26 : you good ? EK ... - Instagram",
          "url": "https://www.instagram.com/p/example/",
          "snippet": "날짜 : 2026.05.10 (일) 장소 : YES24 LIVE HALL 티켓 오픈 : 2026.03.25 19:00 (수)",
          "query": "EK 콘서트 공식 정보",
        },
        {
          "title": "EK 3rd Concert : You Good? (2026.05.10) - StagePick",
          "url": "https://www.stagepick.co.kr/performances/detail/212761",
          "snippet": "공연 시간: 2026. 05. 10 18:00. 공연 장소. 예스24라이브홀.",
          "query": "EK 콘서트 2026 일정 장소",
        },
        {
          "title": "EK 3rd Concert : You Good ? | YES24 LIVE HALL 날짜 및 일정",
          "url": "https://kr.trip.com/events/EK+3rd+Concert++You+Good+-20260330/",
          "snippet": "본 공연은 2026년 7월 20일에 YES24 LIVE HALL에서 열립니다.",
          "query": "EK 콘서트 공식 정보",
        },
      ],
    }
  )

  event_info = result["event_info"]
  assert event_info.title == "EK 3rd Concert : You Good?"
  assert event_info.date_text == "2026.05.10"
  assert event_info.time_text == "18:00"
  assert len(event_info.sources) == 2


def test_extract_event_info_does_not_fill_fields_from_lower_confidence_source() -> None:
  result = extract_event_info(
    {
      "query": "EK 콘서트",
      "input_intent": "concert_or_event_name",
      "input_type": "concert_with_inferred_venue",
      "venue": VenueInfo(name="YES24 Live Hall", aliases=["YES24 LIVE HALL", "예스24라이브홀"]),
      "search_results": [
        {
          "title": "EK 3rd Concert: You Good? - KOPIS 공연 공식 데이터",
          "url": "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id=PF288047",
          "snippet": "공식 KOPIS 공연 데이터. 공연명 EK 3rd Concert: You Good?. 공연기간 2026년 5월 10일. 공연장소 예스24라이브홀.",
          "query": "EK 콘서트 KOPIS 공식 정보 일정 장소",
        },
        {
          "title": "EK 콘서트 관람 후기",
          "url": "https://example.tistory.com/ek-review",
          "snippet": "2026.05.10 18:00 공연으로 기억합니다. 예스24라이브홀 후기입니다.",
          "query": "EK 콘서트 공식 SNS 공지",
        },
      ],
    }
  )

  event_info = result["event_info"]
  assert event_info.confidence_label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert event_info.date_text == "2026년 5월 10일"
  assert event_info.time_text == ""
  assert len(event_info.sources) == 1


def test_extract_event_info_skips_past_dates_for_yearless_query() -> None:
  last_year = date.today().year - 1
  result = extract_event_info(
    {
      "query": "아이유 콘서트 KSPO",
      "input_intent": "concert_or_event_name",
      "input_type": "concert_with_venue_hint",
      "venue": VenueInfo(name="KSPO DOME", aliases=["올림픽체조경기장", "KSPO"]),
      "search_results": [
        {
          "title": f"아이유 콘서트 KSPO ({last_year}.11.22)",
          "url": "https://ticket.example.com/iu-old",
          "snippet": f"아이유 공연은 {last_year}.11.22 KSPO DOME에서 진행되었습니다.",
          "query": "아이유 콘서트 KSPO 공식 정보",
        }
      ],
    }
  )

  assert result == {}


def test_extract_event_info_keeps_requested_past_year() -> None:
  last_year = date.today().year - 1
  result = extract_event_info(
    {
      "query": f"{last_year} 아이유 콘서트 KSPO",
      "input_intent": "concert_or_event_name",
      "input_type": "concert_with_venue_hint",
      "venue": VenueInfo(name="KSPO DOME", aliases=["올림픽체조경기장", "KSPO"]),
      "search_results": [
        {
          "title": f"아이유 콘서트 KSPO ({last_year}.11.22)",
          "url": "https://ticket.example.com/iu-old",
          "snippet": f"아이유 공연은 {last_year}.11.22 KSPO DOME에서 진행되었습니다.",
          "query": f"{last_year} 아이유 콘서트 KSPO 공식 정보",
        }
      ],
    }
  )

  event_info = result["event_info"]
  assert event_info.date_text == f"{last_year}.11.22"
  assert event_info.venue_name == "KSPO DOME"


def test_infer_event_candidates_preserves_date_ranges() -> None:
  current_year = date.today().year
  result = infer_event_candidates(
    {
      "query": "랩비트 페스티벌",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": f"RAPBEAT {current_year} 개최 확정",
          "url": "https://www.instagram.com/p/example/",
          "snippet": f"일정 {current_year}년 6월 20일(토) ~ 21일(일) 2일간 장소 서울 마포 문화비축기지",
          "query": f"랩비트 페스티벌 {current_year} 일정 장소",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].date_text == f"{current_year}년 6월 20일~21일"


def test_official_sns_notice_can_feed_event_candidates_without_overtrusting() -> None:
  result = infer_event_candidates(
    {
      "query": "랩비트 페스티벌",
      "input_intent": "concert_or_event_name",
      "input_type": "unsupported_or_ambiguous",
      "search_results": [
        {
          "title": "RAPBEAT 공식 인스타그램 공지: 서울 2026년 6월 20일 장소: 문화비축기지",
          "url": "https://www.instagram.com/rapbeatfestival/p/example/",
          "snippet": "공식 계정 공지에서 서울 공연 일정과 장소를 안내합니다.",
          "query": "랩비트 페스티벌 공식 SNS 공지",
        }
      ],
    }
  )

  candidates = result["event_candidates"]
  assert candidates[0].region == "서울"
  assert candidates[0].venue_name == "문화비축기지"
  assert candidates[0].confidence_label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED


def test_candidate_summary_asks_user_to_choose() -> None:
  state = {
    "query": "워터밤",
    "input_intent": "concert_or_event_name",
    "input_type": "unsupported_or_ambiguous",
    "search_results": [
      {
        "title": "워터밤 서울 2026 일정 장소: 서울월드컵경기장",
        "url": "https://example.com/waterbomb-seoul",
        "snippet": "서울 공연 공식 공지",
        "query": "워터밤 2026 일정 장소",
      },
      {
        "title": "워터밤 인천 2026 일정 장소: 송도",
        "url": "https://example.com/waterbomb-incheon",
        "snippet": "인천 공연 공식 공지",
        "query": "워터밤 2026 일정 장소",
      },
    ],
  }
  candidate_result = infer_event_candidates(state)
  summary_result = summarize_information({**state, **candidate_result})
  confidence_result = assign_confidence({**state, **candidate_result, **summary_result})

  assert candidate_result["input_type"] == "event_candidates"
  assert any("공연 후보" in item for item in summary_result["summary"])
  assert any("후보" in item for item in confidence_result["confidence_notes"])


def test_summarize_information_prepends_event_info() -> None:
  result = summarize_information(
    {
      "query": "EK 콘서트",
      "venue": VenueInfo(name="YES24 Live Hall"),
      "event_info": EventInfo(
        title="EK 3rd Concert : You Good?",
        date_text="2026.05.10",
        time_text="18:00",
        venue_name="YES24 Live Hall",
      ),
    }
  )

  assert result["summary"][0] == "공연 정보: EK 3rd Concert : You Good? / 2026.05.10 / 18:00 / YES24 Live Hall"


def test_input_analysis_marks_concert_like_queries() -> None:
  result = analyze_input({"query": "아이유 콘서트 KSPO"})

  assert result["input_intent"] == "concert_or_event_name"
  assert result["detail_keywords"] == []


def test_search_queries_preserve_detail_and_localized_input() -> None:
  result = build_search_queries(
    {
      "query": "예스24라이브홀 스탠딩",
      "venue": VenueInfo(name="YES24 Live Hall"),
    }
  )

  queries = [item["query"] for item in result["search_queries"]]
  assert all("YES24 Live Hall" in query for query in queries)
  assert all("예스24라이브홀 스탠딩" in query for query in queries)


def test_search_queries_use_inferred_venue_and_original_concert_query() -> None:
  analysis = analyze_input({"query": "아이유 콘서트 KSPO"})
  venue_state = load_venue_data(analysis)
  result = build_search_queries({**analysis, **venue_state})

  queries = [item["query"] for item in result["search_queries"]]
  assert venue_state["matched_venue_alias"] == "KSPO"
  assert all("KSPO DOME" in query for query in queries)
  assert all("아이유 콘서트 KSPO" in query for query in queries)


def test_search_queries_add_candidate_lookup_only_without_matched_venue() -> None:
  unsupported_result = build_search_queries(
    {
      "query": "워터밤",
      "input_intent": "venue_or_concert_name",
      "venue": None,
    }
  )
  supported_result = build_search_queries(
    {
      "query": "아이유 콘서트 KSPO",
      "input_intent": "concert_or_event_name",
      "venue": VenueInfo(name="KSPO DOME"),
    }
  )

  assert "event_candidates" in [item["purpose"] for item in unsupported_result["search_queries"]]
  assert "event_candidates" not in [item["purpose"] for item in supported_result["search_queries"]]


def test_search_queries_include_official_sns_notice_lookup() -> None:
  result = build_search_queries(
    {
      "query": "랩비트 페스티벌",
      "input_intent": "concert_or_event_name",
      "venue": None,
    }
  )

  assert {
    "query": "랩비트 페스티벌 공식 SNS 공지",
    "purpose": "official_sns",
  } in result["search_queries"]


def test_search_queries_include_public_review_tip_lookups() -> None:
  result = build_search_queries(
    {
      "query": "KSPO DOME 콘서트 준비물",
      "input_intent": "concert_detail_question",
      "venue": VenueInfo(name="KSPO DOME"),
    }
  )

  queries = result["search_queries"]
  assert {
    "query": "KSPO DOME KSPO DOME 콘서트 준비물 관람 후기 꿀팁",
    "purpose": "review_tips",
  } in queries
  assert {
    "query": "KSPO DOME KSPO DOME 콘서트 준비물 입장 대기 스탠딩 후기",
    "purpose": "review_entry",
  } in queries
  assert {
    "query": "KSPO DOME KSPO DOME 콘서트 준비물 물품보관 퇴장 교통 후기",
    "purpose": "review_logistics",
  } in queries


def test_classify_sources_assigns_confidence_after_search() -> None:
  result = classify_sources(
    {
      "search_results": [
        {
          "title": "공연장 관람 후기",
          "url": "https://example.tistory.com/kspo-review",
          "snippet": "공연장 방문 후기와 준비물 팁",
          "query": "KSPO DOME 준비물 팁",
        }
      ]
    }
  )

  source = result["sources"][0]
  assert source.source_type == ConfidenceLabel.PUBLIC_REVIEW_REFERENCE


def test_classify_sources_marks_latest_check_items() -> None:
  result = classify_sources(
    {
      "search_results": [
        {
          "title": "공연 당일 입장 시간 안내",
          "url": "https://example.com/entry-notice",
          "snippet": "입장 시간과 물품보관 운영 여부는 공연별 공지를 확인하세요.",
          "query": "KSPO DOME 입장 시간 물품보관",
        }
      ]
    }
  )

  source = result["sources"][0]
  classified_source = result["classified_sources"][0]
  assert source.source_type == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert "최신 공식 확인" in classified_source["reason"]


def test_summarize_information_adds_public_review_tips() -> None:
  result = summarize_information(
    {
      "query": "KSPO DOME 스탠딩",
      "input_type": "venue_with_detail_question",
      "venue": VenueInfo(name="KSPO DOME", event_check_items=["공연별 입장 시간 확인"]),
      "search_results": [
        {
          "title": "KSPO DOME 스탠딩 입장 후기",
          "url": "https://example.tistory.com/kspo-standing",
          "snippet": "스탠딩 입장 대기와 물품보관 꿀팁을 정리했습니다.",
          "query": "KSPO DOME 입장 대기 스탠딩 후기",
        }
      ],
    }
  )

  assert any(tip.startswith("후기 참고:") for tip in result["transit_and_entry_tips"])
  assert any("스탠딩/입장 대기" in tip for tip in result["transit_and_entry_tips"])
  assert any("물품보관" in tip for tip in result["transit_and_entry_tips"])
  assert result["official_check_required"] == ["공연별 입장 시간 확인"]


def test_summarize_event_candidates_adds_public_review_tips_for_concert_name() -> None:
  result = summarize_information(
    {
      "query": "워터밤",
      "input_type": "event_candidates",
      "venue": None,
      "event_candidates": [EventCandidate(name="워터밤 서울", region="서울")],
      "search_results": [
        {
          "title": "워터밤 준비물 꿀팁 후기",
          "url": "https://blog.naver.com/waterbomb-tip",
          "snippet": "준비물, 물품보관, 퇴장 교통 후기와 입장 대기 팁입니다.",
          "query": "워터밤 관람 후기 꿀팁",
        }
      ],
    }
  )

  assert result["summary"][0] == "검색 결과에서 공연 후보가 확인되었습니다."
  assert "방문하려는 지역/날짜 후보 선택하기" in result["checklist"]
  assert any(tip.startswith("후기 참고:") for tip in result["transit_and_entry_tips"])
  assert any("보조배터리" in tip for tip in result["transit_and_entry_tips"])
  assert any("물품보관" in tip for tip in result["transit_and_entry_tips"])
  assert result["official_check_required"] == ["공연 지역", "공연 날짜", "공연 장소", "입장 시간"]
  assert result["llm_used"] is False


def test_summarize_information_accepts_llm_draft(monkeypatch) -> None:
  def fake_generate_guide_draft_with_fallback(state, fallback_draft):
    return (
      {
        "summary": ["AI 요약"],
        "checklist": ["AI 체크리스트"],
        "transit_and_entry_tips": ["AI 팁"],
        "official_check_required": ["AI 공식 확인"],
      },
      True,
    )

  summarize_module = importlib.import_module("performation_agent.nodes.summarize_information")
  monkeypatch.setattr(summarize_module, "generate_guide_draft_with_fallback", fake_generate_guide_draft_with_fallback)

  result = summarize_module.summarize_information({"query": "KSPO DOME 준비물"})

  assert result["summary"] == ["AI 요약"]
  assert result["checklist"] == ["AI 체크리스트"]
  assert result["llm_used"] is True


def test_summarize_information_preserves_public_review_tips_with_llm(monkeypatch) -> None:
  def fake_generate_guide_draft_with_fallback(state, fallback_draft):
    return (
      {
        "summary": ["AI 요약"],
        "checklist": ["AI 체크리스트"],
        "transit_and_entry_tips": ["AI 팁"],
        "official_check_required": ["AI 공식 확인"],
      },
      True,
    )

  summarize_module = importlib.import_module("performation_agent.nodes.summarize_information")
  monkeypatch.setattr(summarize_module, "generate_guide_draft_with_fallback", fake_generate_guide_draft_with_fallback)

  result = summarize_module.summarize_information(
    {
      "query": "YES24 Live Hall 물품보관",
      "venue": VenueInfo(name="YES24 Live Hall"),
      "search_results": [
        {
          "title": "YES24 Live Hall 물품보관 후기",
          "url": "https://m.blog.naver.com/example/1",
          "snippet": "물품보관 대기와 퇴장 교통 꿀팁을 정리했습니다.",
          "query": "YES24 Live Hall 물품보관 퇴장 교통 후기",
        }
      ],
    }
  )

  assert result["llm_used"] is True
  assert result["transit_and_entry_tips"][0] == "AI 팁"
  assert any(tip.startswith("후기 참고:") for tip in result["transit_and_entry_tips"])


def test_summarize_information_dedupes_and_caps_public_review_tips(monkeypatch) -> None:
  def fake_generate_guide_draft_with_fallback(state, fallback_draft):
    return (
      {
        "summary": ["AI 요약"],
        "checklist": ["AI 체크리스트"],
        "transit_and_entry_tips": [
          "후기 참고: 스탠딩 입장 대기는 일찍 확인하세요.",
          "후기 참고: 물품보관은 빨리 마감될 수 있어요.",
          "후기 참고: 공연 종료 후 지하철 혼잡을 예상하세요.",
          "후기 참고: 보조배터리와 신분증을 챙기세요.",
          "후기 참고: 주변 편의점 위치를 확인하세요.",
          "후기 참고: 식사는 미리 하고 오세요.",
          "후기 참고: 우비를 챙기세요.",
        ],
        "official_check_required": ["AI 공식 확인"],
      },
      True,
    )

  summarize_module = importlib.import_module("performation_agent.nodes.summarize_information")
  monkeypatch.setattr(summarize_module, "generate_guide_draft_with_fallback", fake_generate_guide_draft_with_fallback)

  result = summarize_module.summarize_information(
    {
      "query": "워터밤 준비물 꿀팁",
      "search_results": [
        {
          "title": "워터밤 물품보관 후기",
          "url": "https://blog.naver.com/example/1",
          "snippet": "물품보관과 퇴장 교통 꿀팁입니다.",
          "query": "워터밤 물품보관 퇴장 교통 후기",
        }
      ],
    }
  )

  review_tips = [tip for tip in result["transit_and_entry_tips"] if tip.startswith("후기 참고:")]
  assert len(review_tips) == 6
  assert sum("물품보관" in tip for tip in review_tips) == 1
