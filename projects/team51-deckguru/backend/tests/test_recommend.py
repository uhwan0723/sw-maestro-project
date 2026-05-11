import pytest

from app.rag.service import RagUnavailableError
from app.services.strategy_invoker import RecommendationFailed, RecommendationTimeout


VALID_BODY = {
    "tier": "GOLD",
    "play_style": "stable_top4",
    "question": "현재 패치 추천 덱 알려줘",
}


@pytest.mark.asyncio
async def test_recommend_success(client):
    resp = await client.post("/api/recommend", json=VALID_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert "decks" in data
    assert "intent" in data
    assert "confidence" in data
    assert resp.headers.get("X-Cache") == "MISS"
    assert resp.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_recommend_cache_hit(client):
    await client.post("/api/recommend", json=VALID_BODY)
    resp2 = await client.post("/api/recommend", json=VALID_BODY)
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache") == "HIT"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "status_code", "code"),
    [
        (RecommendationTimeout("slow"), 504, "agent_timeout"),
        (RecommendationFailed("schema failed"), 502, "agent_failed"),
        (RagUnavailableError("missing collection"), 502, "rag_unavailable"),
        (RuntimeError("boom"), 500, "agent_internal"),
    ],
)
async def test_recommend_error_mapping(client, monkeypatch, exc, status_code, code):
    async def failing_agent(*args, **kwargs):
        raise exc

    monkeypatch.setattr("app.api.recommend.run_strategy_agent", failing_agent)

    resp = await client.post(
        "/api/recommend",
        json={**VALID_BODY, "question": f"{VALID_BODY['question']} {code}"},
    )
    assert resp.status_code == status_code
    assert resp.json()["detail"]["code"] == code


@pytest.mark.asyncio
async def test_recommend_missing_field(client):
    resp = await client.post("/api/recommend", json={"tier": "GOLD"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recommend_question_too_long(client):
    body = {**VALID_BODY, "question": "a" * 501}
    resp = await client.post("/api/recommend", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recommend_invalid_tier(client):
    body = {**VALID_BODY, "tier": "MYTHIC"}
    resp = await client.post("/api/recommend", json=body)
    assert resp.status_code == 422
