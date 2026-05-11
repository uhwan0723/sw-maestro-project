"""Stable backend import path for invoking the Strategy Agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from app.agents.strategy.api import (
    RecommendationFailed,
    RecommendationTimeout,
    run_strategy_agent as run_real_strategy_agent,
)
from app.schemas.api import RecommendationResponse
from app.schemas.shared import PlayStyle, Tier
from app.settings import settings

logger = structlog.get_logger()

_MOCK_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "mock_responses"
    / "recommend_deck_gold_stable.json"
)


async def run_strategy_agent(
    request_id: str,
    tier: Tier,
    play_style: PlayStyle,
    question: str,
    *,
    patch_version: str,
    timeout_s: float = 25.0,
) -> RecommendationResponse:
    if settings.mock_strategy_agent:
        logger.info(
            "strategy_mock_response",
            request_id=request_id,
            stage="strategy",
            fixture=_MOCK_PATH.name,
        )
        return _load_mock_response(request_id=request_id, patch_version=patch_version)

    return await run_real_strategy_agent(
        request_id=request_id,
        tier=tier,
        play_style=play_style,
        question=question,
        patch_version=patch_version,
        timeout_s=timeout_s,
    )


def _load_mock_response(*, request_id: str, patch_version: str) -> RecommendationResponse:
    data = json.loads(_MOCK_PATH.read_text(encoding="utf-8"))
    data["request_id"] = request_id
    data["patch_version"] = patch_version
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    return RecommendationResponse(**data)


__all__ = [
    "run_strategy_agent",
    "RecommendationTimeout",
    "RecommendationFailed",
]
