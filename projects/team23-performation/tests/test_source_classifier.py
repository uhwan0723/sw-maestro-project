from performation_agent.tools.source_classifier import classify_search_result
from performation_domain import ConfidenceLabel


def test_classifies_official_venue_source() -> None:
  label, reason = classify_search_result(
    {
      "title": "KSPO DOME 공연장 안내",
      "url": "https://www.ksponco.or.kr/olympicpark/menu.es?mid=a20301030800",
      "snippet": "올림픽공원 공식 공연장 안내입니다.",
      "query": "KSPO DOME 공식 정보",
    }
  )

  assert label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert "공식" in reason


def test_public_review_domain_overrides_official_keywords() -> None:
  label, reason = classify_search_result(
    {
      "title": "KSPO DOME 관람 후기",
      "url": "https://example.tistory.com/kspo-review",
      "snippet": "공식 공지를 보고 방문한 후기와 준비물 팁입니다.",
      "query": "KSPO DOME 준비물 팁",
    }
  )

  assert label == ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  assert "참고용" in reason


def test_event_specific_information_requires_latest_official_check() -> None:
  label, reason = classify_search_result(
    {
      "title": "공연별 입장 시간과 물품보관 안내",
      "url": "https://example.com/event-entry",
      "snippet": "입장 시간, 입장 위치, 물품보관 운영 여부는 공연별로 달라질 수 있습니다.",
      "query": "YES24 Live Hall 입장 시간 물품보관",
    }
  )

  assert label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert "최신 공식 확인" in reason


def test_official_sns_notice_requires_latest_official_check() -> None:
  label, reason = classify_search_result(
    {
      "title": "RAPBEAT 공식 인스타그램 공지",
      "url": "https://www.instagram.com/rapbeatfestival/p/example/",
      "snippet": "공식 계정 공지에서 일정과 장소를 안내합니다.",
      "query": "랩비트 페스티벌 공식 SNS 공지",
    }
  )

  assert label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert "SNS" in reason


def test_threads_dot_com_is_treated_as_sns() -> None:
  label, reason = classify_search_result(
    {
      "title": "EK 공식 Threads 공지",
      "url": "https://www.threads.com/@mba_ek/post/example",
      "snippet": "공식 계정 공지에서 일정과 장소를 안내합니다.",
      "query": "EK 콘서트 공식 SNS 공지",
    }
  )

  assert label == ConfidenceLabel.LATEST_OFFICIAL_CHECK_REQUIRED
  assert "SNS" in reason


def test_unverified_sns_post_is_uncertain() -> None:
  label, reason = classify_search_result(
    {
      "title": "워터밤 일정 공유",
      "url": "https://x.com/random_account/status/1",
      "snippet": "일정이 올라왔다는 글입니다.",
      "query": "워터밤 공식 SNS 공지",
    }
  )

  assert label == ConfidenceLabel.UNCERTAIN
  assert "SNS" in reason


def test_fan_sns_review_stays_public_reference() -> None:
  label, reason = classify_search_result(
    {
      "title": "워터밤 팬 후기",
      "url": "https://www.youtube.com/watch?v=example",
      "snippet": "팬 브이로그와 관람 리뷰입니다.",
      "query": "워터밤 공식 SNS 공지",
    }
  )

  assert label == ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  assert "참고용" in reason


def test_tiktok_tip_post_stays_public_reference() -> None:
  label, reason = classify_search_result(
    {
      "title": "KSPO DOME 스탠딩 입장 꿀팁",
      "url": "https://www.tiktok.com/@concert_tip/video/example",
      "snippet": "입장 대기와 스탠딩 관람팁을 정리한 영상입니다.",
      "query": "KSPO DOME 입장 대기 스탠딩 후기",
    }
  )

  assert label == ConfidenceLabel.PUBLIC_REVIEW_REFERENCE
  assert "참고용" in reason


def test_unknown_source_remains_uncertain() -> None:
  label, reason = classify_search_result(
    {
      "title": "공연장 정보 모음",
      "url": "https://example.com/venue",
      "snippet": "여러 공연장의 일반 정보를 모았습니다.",
      "query": "처음 보는 공연장",
    }
  )

  assert label == ConfidenceLabel.UNCERTAIN
  assert "불확실" in reason


def test_query_terms_do_not_drive_source_classification() -> None:
  label, reason = classify_search_result(
    {
      "title": "공연장 정보 모음",
      "url": "https://example.com/venue",
      "snippet": "여러 공연장의 일반 정보를 모았습니다.",
      "query": "KSPO DOME 공식 후기",
    }
  )

  assert label == ConfidenceLabel.UNCERTAIN
  assert "불확실" in reason


def test_official_notice_source_stays_official_when_no_event_specific_detail() -> None:
  label, reason = classify_search_result(
    {
      "title": "KSPO DOME 공지사항",
      "url": "https://www.ksponco.or.kr/olympicpark/notice",
      "snippet": "올림픽공원 공식 공지사항입니다.",
      "query": "KSPO DOME 공지",
    }
  )

  assert label == ConfidenceLabel.OFFICIAL_CONFIRMED
  assert "공식" in reason
