import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "patch_version" in data
    assert "rag_chunks" in data
    assert "uptime_s" in data


@pytest.mark.asyncio
async def test_patch_info_returns_200(client):
    resp = await client.get("/api/patch-info")
    assert resp.status_code == 200
    data = resp.json()
    assert "patch_version" in data
    assert "warnings" in data


@pytest.mark.asyncio
async def test_example_questions(client):
    resp = await client.get("/api/example-questions")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 4
    intents = {item["intent"] for item in items}
    assert intents == {"recommend_deck", "deck_playstyle", "item_pivot", "patch_summary"}
