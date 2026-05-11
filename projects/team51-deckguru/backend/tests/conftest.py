import json
from datetime import datetime, timezone
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.api import RecommendationResponse

_MOCK_PATH = (
    Path(__file__).parent / "fixtures" / "mock_responses" / "recommend_deck_gold_stable.json"
)


async def _mock_agent(request_id, tier, play_style, question, *, patch_version, timeout_s=25.0):
    data = json.loads(_MOCK_PATH.read_text(encoding="utf-8"))
    data["request_id"] = request_id
    data["patch_version"] = patch_version
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    return RecommendationResponse(**data)


@pytest_asyncio.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.api.recommend.run_strategy_agent",
        _mock_agent,
    )

    db_file = tmp_path / "test.db"
    monkeypatch.setattr("app.settings.settings.sqlite_path", db_file)

    from app.services import cache as cache_mod
    from app.services import feedback_store as fb_mod
    from app.services.limiter import limiter

    cache_mod.cache_service = cache_mod.CacheService()
    fb_mod.feedback_store = fb_mod.FeedbackStore()
    limiter.reset()

    await cache_mod.cache_service.init_db()
    await fb_mod.feedback_store.init_db()

    monkeypatch.setattr("app.api.recommend.cache_service", cache_mod.cache_service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
