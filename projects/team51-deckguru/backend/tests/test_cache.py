from app.services.normalize import cache_key, normalize_question


def test_normalize_trailing_punct():
    assert normalize_question("추천해줘?") == "추천해줘"
    assert normalize_question("추천해줘!") == "추천해줘"
    assert normalize_question("추천해줘...") == "추천해줘"


def test_normalize_whitespace():
    assert normalize_question("골드  추천   해줘") == "골드 추천 해줘"
    assert normalize_question("  앞뒤공백  ") == "앞뒤공백"


def test_normalize_case():
    assert normalize_question("GOLD 덱") == "gold 덱"


def test_cache_key_equivalence():
    k1 = cache_key("GOLD", "stable_top4", "추천해줘", "17.2")
    k2 = cache_key("GOLD", "stable_top4", "추천해줘?", "17.2")
    k3 = cache_key("GOLD", "stable_top4", "추천해줘!", "17.2")
    assert k1 == k2 == k3


def test_cache_key_patch_differs():
    k1 = cache_key("GOLD", "stable_top4", "추천해줘", "17.2")
    k2 = cache_key("GOLD", "stable_top4", "추천해줘", "17.3")
    assert k1 != k2


def test_cache_key_tier_differs():
    k1 = cache_key("GOLD", "stable_top4", "추천해줘", "17.2")
    k2 = cache_key("PLATINUM", "stable_top4", "추천해줘", "17.2")
    assert k1 != k2
