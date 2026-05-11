"""Live Research 통합 경로의 최소 회귀 테스트.

실제 DuckDuckGo/외부 페이지/Solar를 호출하면 테스트가 느리고 불안정해진다.
그래서 graph의 도구 함수를 monkeypatch해 고정된 검색 결과와 페이지 본문을
주입하고, `run_live_research()`가 fallback만으로도 fact/source/queue를 만드는지
검증한다.
"""

from __future__ import annotations

import json

import pytest

from app.research.api import run_live_research
from app.research.state import PageContent, SearchResult


pytestmark = pytest.mark.asyncio


async def test_run_live_research_collects_facts_with_fallback_tools(monkeypatch, tmp_path):
    """LLM/API 키 없이도 검색 -> fetch -> fact 추출이 끝까지 이어지는지 검증."""
    from app.agents.strategy import llm as llm_mod
    import app.research.graph as graph_mod
    import app.research.nodes.extract_facts as extract_mod
    import app.research.nodes.plan as plan_mod

    # 테스트는 실제 backend/data를 오염시키지 않도록 캐시와 promotion queue를
    # pytest tmp_path 아래로 격리한다.
    monkeypatch.setenv("LIVE_RESEARCH_ENABLED", "true")
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    monkeypatch.delenv("RESEARCH_LLM_PLANNER_ENABLED", raising=False)
    monkeypatch.delenv("RESEARCH_LLM_EXTRACT_ENABLED", raising=False)
    monkeypatch.setattr(llm_mod.settings, "upstage_api_key", "")
    monkeypatch.setenv("RESEARCH_CACHE_PATH", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("PROMOTION_QUEUE_PATH", str(tmp_path / "promotion_queue.jsonl"))

    async def fail_if_llm_called(*args, **kwargs):
        raise AssertionError("fallback live research should not call the research LLM")

    source_url = (
        "https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/"
        "tft-patch-14-9-notes/"
    )

    async def fake_search(query: str, *, k: int = 5) -> list[SearchResult]:
        """DuckDuckGo 대신 고정된 whitelist 검색 결과를 반환한다."""
        return [
            SearchResult(
                title="TFT patch 14.9 notes",
                url=source_url,
                snippet="TFT patch 14.9 updates several traits and items for the current meta.",
                published_at="2026-05-01T00:00:00Z",
            )
        ]

    async def fake_fetch(url: str) -> PageContent:
        """fetch_page 대신 fact 추출에 충분한 고정 본문을 반환한다."""
        return PageContent(
            url=url,
            title="TFT patch 14.9 notes",
            text=(
                "TFT patch 14.9 updates several traits and items for the current meta. "
                "The official patch notes describe balance changes that affect deck "
                "selection and item priority for ranked games."
            ),
            published_at="2026-05-01T00:00:00Z",
        )

    monkeypatch.setattr(graph_mod, "web_search", fake_search)
    monkeypatch.setattr(graph_mod, "fetch_page", fake_fetch)
    monkeypatch.setattr(llm_mod, "call_structured", fail_if_llm_called)
    monkeypatch.setattr(plan_mod, "call_structured", fail_if_llm_called)
    monkeypatch.setattr(extract_mod, "call_structured", fail_if_llm_called)

    result = await run_live_research(
        "research-test-1",
        question="latest TFT patch 14.9 current meta recommendation",
        extracted_keywords=["patch 14.9", "current meta"],
        patch_version="14.9",
        max_steps=3,
        timeout_s=5.0,
    )

    assert result.research_steps >= 2
    assert result.web_facts
    assert result.sources
    assert result.sources[0].source_kind == "patch_note_official"
    assert "live_research_not_implemented" not in result.warnings

    # promotion queue에 쌓이는 JSONL도 request_id/patch_version을 함께 보존해야
    # 이후 사람이 검토해서 RAG 후보로 승격할 수 있다.
    queue_path = tmp_path / "promotion_queue.jsonl"
    queued = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
    assert queued[0]["request_id"] == "research-test-1"
    assert queued[0]["patch_version"] == "14.9"


async def test_run_live_research_disabled_by_env(monkeypatch):
    """환경변수로 Live Research를 끄면 외부 도구 없이 빈 결과를 반환한다."""
    monkeypatch.setenv("LIVE_RESEARCH_ENABLED", "false")

    result = await run_live_research(
        "research-test-disabled",
        question="latest TFT patch",
        extracted_keywords=[],
        patch_version="14.9",
    )

    assert result.web_facts == []
    assert result.warnings == ["live_research_disabled_by_env"]
