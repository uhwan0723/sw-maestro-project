"""Strategy Agent 내부의 live_research 노드.

이 파일은 `backend/app/research`의 실제 Live Research 구현을 StrategyState에
연결하는 어댑터다.

역할:
- StrategyState에서 question/keywords/patch_version을 꺼내 Research API에 넘긴다.
- ResearchResult의 web_facts/sources/research_steps를 StrategyState에 병합한다.
- 설정된 예산을 넘기면 추천 전체를 실패시키지 않고 `research_truncated` warning만 남긴다.
"""

from __future__ import annotations

import asyncio
import time

import structlog

from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.research.api import run_live_research
from app.settings import settings

logger = structlog.get_logger()


async def live_research(state: StrategyState) -> dict:
    """Live Research 결과를 StrategyState에 병합한다."""
    state.need_live = True
    timeout_s = max(0.5, settings.live_research_timeout_s)
    max_steps = max(1, min(settings.live_research_max_steps, 5))
    started = time.perf_counter()
    logger.info(
        "live_research_start",
        request_id=state.request_id,
        stage="research",
        timeout_s=timeout_s,
        max_steps=max_steps,
    )
    try:
        # Research API 내부에도 timeout_s가 있지만, Strategy graph 차원에서도
        # asyncio.wait_for로 한 번 더 감싸 전체 agent timeout을 보호한다.
        result = await asyncio.wait_for(
            run_live_research(
                request_id=state.request_id,
                question=state.question,
                extracted_keywords=state.extracted_keywords,
                patch_version=state.patch_version,
                max_steps=max_steps,
                timeout_s=timeout_s,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        state.node_latencies_ms["live_research"] = elapsed_ms(started)
        logger.warning(
            "live_research_timeout",
            request_id=state.request_id,
            stage="research",
            latency_ms=state.node_latencies_ms["live_research"],
        )
        state.warnings.append("research_truncated")
        return state.model_dump()

    # web_facts는 이후 analyze_meta/recommend prompt의 live evidence로 쓰이고,
    # sources는 최종 RecommendationResponse.sources에 그대로 노출된다.
    state.web_facts = result.web_facts
    state.sources.extend(result.sources)
    state.research_steps = result.research_steps
    state.warnings.extend(result.warnings)
    if result.truncated:
        state.warnings.append("research_truncated")

    state.node_latencies_ms["live_research"] = elapsed_ms(started)
    logger.info(
        "live_research_done",
        request_id=state.request_id,
        stage="research",
        web_facts=len(state.web_facts),
        sources=len(state.sources),
        steps=state.research_steps,
        warnings=len(result.warnings),
        latency_ms=state.node_latencies_ms["live_research"],
    )
    return state.model_dump()
