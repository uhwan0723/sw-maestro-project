import asyncio

import pytest

from app.agents.strategy.nodes import live_research as live_research_mod
from app.agents.strategy.state import StrategyState
from app.research.state import ResearchResult


pytestmark = pytest.mark.asyncio


def _state() -> StrategyState:
    return StrategyState(
        request_id="live-node-test",
        patch_version="17.2",
        tier="GOLD",
        play_style="stable_top4",
        question="최신 메타 덱 추천해줘",
        intent="recommend_deck",
        extracted_keywords=["최신", "메타"],
    )


async def test_live_research_uses_short_configured_budget(monkeypatch):
    captured = {}

    async def fake_run_live_research(**kwargs):
        captured.update(kwargs)
        return ResearchResult(research_steps=1)

    monkeypatch.setattr(live_research_mod.settings, "live_research_timeout_s", 3.0)
    monkeypatch.setattr(live_research_mod.settings, "live_research_max_steps", 2)
    monkeypatch.setattr(live_research_mod, "run_live_research", fake_run_live_research)

    out = await live_research_mod.live_research(_state())

    assert out["need_live"] is True
    assert captured["timeout_s"] == 3.0
    assert captured["max_steps"] == 2


async def test_live_research_timeout_degrades_to_rag_only(monkeypatch):
    async def fake_run_live_research(**kwargs):
        raise asyncio.TimeoutError

    monkeypatch.setattr(live_research_mod.settings, "live_research_timeout_s", 3.0)
    monkeypatch.setattr(live_research_mod.settings, "live_research_max_steps", 2)
    monkeypatch.setattr(live_research_mod, "run_live_research", fake_run_live_research)

    out = await live_research_mod.live_research(_state())

    assert out["need_live"] is True
    assert "research_truncated" in out["warnings"]
    assert out["web_facts"] == []
