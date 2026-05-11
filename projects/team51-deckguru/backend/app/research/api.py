"""Live Research의 외부 진입점.

Owner: Agent-3 (04-agent-research-spec.md).
Caller: Agent-1 (Strategy).

Strategy Agent는 이 파일의 `run_live_research()`만 호출한다. 내부 구현이
ReAct 루프인지, 규칙 기반 fallback인지, 캐시를 쓰는지는 Strategy 입장에서는
몰라도 된다.

중요한 설계 원칙:
- 외부 검색/페이지 fetch는 실패할 수 있으므로 예외를 밖으로 던지지 않는다.
- 실패하면 warnings에 기록하고 빈 결과 또는 부분 결과를 반환한다.
- Strategy는 그 결과를 보고 RAG-only 답변으로 자연스럽게 degrade한다.
"""

from __future__ import annotations

import os
import time

import structlog

from app.observability import elapsed_ms
from app.research.graph import run_research_loop
from app.research.promotion_queue import enqueue_facts
from app.research.state import ResearchResult, ResearchState
from app.research.whitelist import domain_from_url, source_kind_for_url
from app.schemas.shared import Source, WebFact

logger = structlog.get_logger()


def _sources_from_facts(facts: list[WebFact]) -> list[Source]:
    """WebFact 목록에서 응답용 Source 목록을 만든다.

    `WebFact`는 fact와 source가 1:1로 연결된 내부 evidence이고,
    `Source`는 최종 RecommendationResponse에 노출되는 출처 카드용 모델이다.
    같은 URL에서 여러 fact가 나올 수 있으므로 URL 기준으로 중복 제거한다.
    """
    sources: list[Source] = []
    seen: set[str] = set()
    for fact in facts:
        url = str(fact.source_url)
        key = url.rstrip("/")
        if key in seen:
            continue

        title = fact.source_title or domain_from_url(url) or "Live research source"
        snippet = (fact.quote or fact.text).strip()[:200] or title
        sources.append(
            Source(
                title=title,
                url=url,
                published_at=fact.published_at,
                snippet=snippet,
                source_kind=source_kind_for_url(url),
            )
        )
        seen.add(key)
    return sources


async def run_live_research(
    request_id: str,
    *,
    question: str,
    extracted_keywords: list[str],
    patch_version: str,
    max_steps: int = 5,
    timeout_s: float = 15.0,
) -> ResearchResult:
    """최대 `timeout_s` 안에서 Live Research를 실행하고 결과를 반환한다."""
    started = time.perf_counter()
    logger.info(
        "research_api_start",
        request_id=request_id,
        stage="research",
        max_steps=max_steps,
        timeout_s=timeout_s,
        patch_version=patch_version,
    )
    if os.getenv("LIVE_RESEARCH_ENABLED", "true").lower() != "true":
        logger.info(
            "research_api_skip",
            request_id=request_id,
            stage="research",
            reason="disabled_by_env",
        )
        return ResearchResult(warnings=["live_research_disabled_by_env"])

    state = ResearchState(
        request_id=request_id,
        patch_version=patch_version,
        question=question,
        extracted_keywords=extracted_keywords,
    )

    try:
        # 실제 ReAct 루프. 검색/페이지 도구 호출과 fact 추출이 여기서 일어난다.
        state = await run_research_loop(
            state,
            max_steps=max_steps,
            timeout_s=timeout_s,
        )
    except Exception as exc:
        # Strategy Agent까지 예외를 전파하면 전체 추천이 실패한다.
        # Live Research는 보조 신호이므로 경고만 남기고 RAG-only 경로를 살린다.
        logger.warning(
            "research_api_failed",
            request_id=request_id,
            stage="research",
            error=str(exc),
        )
        state.errors.append(f"live_research_failed: {exc}")

    state.sources = _sources_from_facts(state.extracted_facts)
    if not state.extracted_facts and not state.warnings:
        state.warnings.append("live_research_no_facts")

    try:
        # Live에서 얻은 fact는 즉시 RAG 인덱스에 넣지 않는다.
        # 검토 전 인덱싱은 품질 위험이 있으므로 JSONL 큐에만 쌓아 둔다.
        await enqueue_facts(
            request_id,
            state.extracted_facts,
            patch_version=patch_version,
        )
    except OSError as exc:
        state.warnings.append(f"promotion_queue_failed: {exc}")

    warnings = list(dict.fromkeys([*state.warnings, *state.errors]))
    result = ResearchResult(
        web_facts=state.extracted_facts,
        sources=state.sources,
        research_steps=len(state.react_log),
        domains_visited=state.domains_visited,
        truncated=state.truncated,
        latency_ms=int((time.perf_counter() - started) * 1000),
        warnings=warnings,
    )
    logger.info(
        "research_api_done",
        request_id=request_id,
        stage="research",
        web_facts=len(result.web_facts),
        sources=len(result.sources),
        steps=result.research_steps,
        truncated=result.truncated,
        warnings=len(result.warnings),
        latency_ms=elapsed_ms(started),
    )
    return result


__all__ = ["ResearchResult", "run_live_research"]
