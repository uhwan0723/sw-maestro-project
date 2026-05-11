from performation_venue_data import get_default_repository


def test_repository_matches_normalized_venue_aliases() -> None:
  repository = get_default_repository()

  examples = [
    ("아이유 콘서트 KSPO", "KSPO DOME"),
    ("올림픽 체조 경기장 입장", "KSPO DOME"),
    ("블루스퀘어 마스터카드홀 공연", "Blue Square"),
    ("예스24 라이브 홀 스탠딩", "YES24 Live Hall"),
  ]

  for query, venue_name in examples:
    venue = repository.find_by_query(query)
    assert venue is not None
    assert venue.name == venue_name


def test_repository_does_not_guess_without_supported_venue_hint() -> None:
  repository = get_default_repository()

  assert repository.find_by_query("아이유 콘서트 티켓팅") is None


def test_repository_does_not_guess_when_multiple_supported_venues_match() -> None:
  repository = get_default_repository()

  matches = repository.find_matches_by_query("KSPO 블루스퀘어 공연")

  assert {match.venue.name for match in matches} == {"KSPO DOME", "Blue Square"}
  assert repository.find_by_query("KSPO 블루스퀘어 공연") is None
