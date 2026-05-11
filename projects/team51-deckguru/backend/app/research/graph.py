"""Live Research의 ReAct 실행 루프.

이 모듈은 "어떤 도구를 부를지 정하고(plan), 실제로 부르고(act), 결과를
관찰로 저장하고(observe), 마지막에 fact를 추출(extract)"하는 전체 흐름을
담당한다.

LangGraph 객체를 직접 쓰지는 않지만, spec의 ReAct sub-graph 책임을 같은
단계 구조로 구현한다. 외부 검색 결과는 시점에 따라 달라질 수 있으므로
도구 결과를 SQLite 캐시에 저장해 같은 입력을 7일 동안 재현 가능하게 한다.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import structlog

from app.observability import elapsed_ms, preview
from app.research.cache import get_cached_json, set_cached_json
from app.research.nodes.extract_facts import extract_facts, fallback_extract
from app.research.nodes.plan import fallback_plan, plan_next_action
from app.research.state import (
    Observation,
    PageContent,
    PlanDecision,
    ReActStep,
    ResearchState,
    SearchResult,
)
from app.research.tools.base import ResearchToolError
from app.research.tools.fetch_page import fetch_page
from app.research.tools.web_search import web_search
from app.research.whitelist import domain_from_url

logger = structlog.get_logger()


def _timeout_cap(env_key: str, default: float) -> float:
    """LLM plan/reflect/extract 단계별 timeout cap을 환경변수에서 읽는다.

    잘못된 값이 들어오면 research 전체가 실패하지 않도록 기본값으로 되돌린다.
    """
    try:
        return float(os.getenv(env_key, default))
    except ValueError:
        return default


def _tool_timeout(tool: str) -> float:
    """도구별 내부 timeout 상한.

    전체 `timeout_s`가 15초여도 fetch_page는 검색보다 오래 걸릴 수 있으므로
    도구별 cap을 다르게 둔다. 실제 timeout은 전체 deadline과 이 cap 중
    더 작은 값이 사용된다.
    """
    if tool == "fetch_page":
        return 6.0
    return 3.5


def _remaining(deadline: float, cap: float) -> float:
    """전체 deadline을 넘지 않는 선에서 이번 작업에 쓸 수 있는 시간."""
    return max(0.1, min(cap, deadline - time.monotonic()))


async def _with_deadline(coro, *, deadline: float, cap: float):
    """개별 awaitable에 전체 deadline 기반 timeout을 적용한다."""
    return await asyncio.wait_for(coro, timeout=_remaining(deadline, cap))


def _normalize_plan(plan: PlanDecision, state: ResearchState) -> PlanDecision:
    """LLM 또는 fallback이 만든 tool_input을 실행 가능한 형태로 보정한다."""
    if plan.tool == "web_search":
        # 검색어가 비었으면 원 질문을 쓰고, 너무 긴 query는 검색엔진 요청 실패를
        # 피하기 위해 300자로 제한한다.
        query = str(plan.tool_input.get("query") or state.question).strip()
        k_raw = plan.tool_input.get("k", 5)
        try:
            k = int(k_raw)
        except (TypeError, ValueError):
            k = 5
        # k가 너무 크면 응답이 느려지고 토큰도 늘어나므로 1~8 사이로 제한한다.
        plan.tool_input = {"query": query[:300], "k": min(max(k, 1), 8)}
    elif plan.tool == "fetch_page":
        plan.tool_input = {"url": str(plan.tool_input.get("url") or "").strip()}
    return plan


def _track_domains(state: ResearchState, observations: list[Observation]) -> None:
    """방문/관찰한 도메인을 중복 없이 기록한다."""
    seen = set(state.domains_visited)
    for obs in observations:
        if obs.url:
            domain = domain_from_url(str(obs.url))
            if domain and domain not in seen:
                state.domains_visited.append(domain)
                seen.add(domain)
        for result in obs.raw.get("results", []):
            url = str(result.get("url") or "")
            if not url:
                continue
            domain = domain_from_url(url)
            if domain and domain not in seen:
                state.domains_visited.append(domain)
                seen.add(domain)


def _search_observation(query: str, results: list[SearchResult]) -> Observation:
    """SearchResult 목록을 ReAct 공통 관찰 모델로 변환한다."""
    text = "\n".join(
        f"{idx + 1}. {result.title}: {result.snippet}"
        for idx, result in enumerate(results)
    )
    return Observation(
        tool="web_search",
        title=f"Search results: {query}",
        text=text or "No whitelisted search results.",
        raw={"results": [result.model_dump(mode="json") for result in results]},
    )


def _page_observation(page: PageContent) -> Observation:
    """PageContent를 ReAct 공통 관찰 모델로 변환한다."""
    return Observation(
        tool="fetch_page",
        url=page.url,
        title=page.title,
        text=page.text,
        fetched_at=page.fetched_at,
        published_at=page.published_at,
        raw=page.model_dump(mode="json"),
    )


async def _act_plan(
    state: ResearchState,
    plan: PlanDecision,
) -> tuple[list[Observation], str]:
    """plan이 선택한 도구를 실행하고 Observation 목록으로 반환한다.

    도구 입력을 cache key로 삼기 때문에 같은 검색어/URL/영상 ID는 캐시 hit가
    난다. 캐시는 성능 목적도 있지만, 외부 정보가 변해도 디버깅 시 당시 결과를
    다시 볼 수 있게 하는 목적이 더 크다.
    """
    tool = plan.tool
    tool_input = plan.tool_input

    try:
        cached = await get_cached_json(tool, tool_input)
        if tool == "web_search":
            if cached is None:
                # DuckDuckGo HTML 검색 후 whitelisted URL만 SearchResult로 들어온다.
                results = await web_search(
                    str(tool_input["query"]),
                    k=int(tool_input.get("k", 5)),
                )
                cached = [result.model_dump(mode="json") for result in results]
                await set_cached_json(tool, tool_input, cached)
            results = [SearchResult.model_validate(item) for item in cached]
            return [_search_observation(str(tool_input["query"]), results)], (
                f"{len(results)} whitelisted search results"
            )

        if tool == "fetch_page":
            if cached is None:
                # fetch_page 내부에서 whitelist와 robots.txt 검사를 모두 수행한다.
                page = await fetch_page(str(tool_input["url"]))
                cached = page.model_dump(mode="json")
                await set_cached_json(tool, tool_input, cached)
            page = PageContent.model_validate(cached)
            return [_page_observation(page)], (
                f"Fetched {len(page.text)} chars from {page.title or page.url}"
            )

    except (ResearchToolError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        # 도구 실패는 Live Research 전체 실패가 아니다. 에러를 state에 남기고
        # 다음 step에서 다른 도구/검색어를 시도할 수 있게 한다.
        state.errors.append(f"{tool}_failed: {exc}")
        return [], f"{tool} failed: {exc}"

    return [], f"{tool} produced no observation"


async def run_research_loop(
    state: ResearchState,
    *,
    max_steps: int = 5,
    timeout_s: float = 15.0,
) -> ResearchState:
    """bounded ReAct loop의 메인 함수."""
    started = time.perf_counter()
    deadline = time.monotonic() + timeout_s
    max_steps = min(max(max_steps, 1), 5)
    logger.info(
        "research_loop_start",
        request_id=state.request_id,
        stage="research",
        max_steps=max_steps,
        timeout_s=timeout_s,
    )

    for step_no in range(1, max_steps + 1):
        if time.monotonic() >= deadline:
            state.truncated = True
            break

        state.step = step_no
        try:
            # 1. plan: LLM이 다음 도구를 고른다. LLM 실패 시 규칙 기반 fallback.
            plan = await _with_deadline(
                plan_next_action(state),
                deadline=deadline,
                cap=_timeout_cap("RESEARCH_PLAN_TIMEOUT_S", 8.0),
            )
        except asyncio.TimeoutError:
            # Solar가 느려 plan이 3초 안에 끝나지 않더라도 전체 research를
            # 중단하지 않는다. deterministic planner로 넘어가 검색을 계속한다.
            state.warnings.append("research_plan_timeout_fallback")
            plan = fallback_plan(state)

        plan = _normalize_plan(plan, state)
        logger.info(
            "research_step_plan",
            request_id=state.request_id,
            stage="research",
            step=step_no,
            tool=plan.tool,
            tool_input=preview(plan.tool_input, limit=120),
        )
        try:
            # 2. act/observe: 도구를 실행하고 결과를 Observation으로 표준화한다.
            observations, summary = await _with_deadline(
                _act_plan(state, plan),
                deadline=deadline,
                cap=_tool_timeout(plan.tool),
            )
        except asyncio.TimeoutError:
            state.truncated = True
            state.warnings.append("research_truncated")
            break

        state.raw_observations.extend(observations)
        _track_domains(state, observations)
        logger.info(
            "research_step_observe",
            request_id=state.request_id,
            stage="research",
            step=step_no,
            tool=plan.tool,
            observations=len(observations),
            summary=preview(summary, limit=120),
        )
        # 사용자가 DEMO_MODE에서 react_steps를 볼 수 있고, 개발자는 어느 도구가
        # 어떤 입력으로 실행됐는지 추적할 수 있다.
        state.react_log.append(
            ReActStep(
                step=step_no,
                thought=plan.thought,
                tool=plan.tool,
                tool_input=plan.tool_input,
                observation_summary=summary[:500],
            )
        )

        if not observations and step_no >= 2:
            # 두 번째 step 이후에도 관찰이 없으면 같은 실패를 반복할 가능성이 높다.
            break

    if time.monotonic() >= deadline:
        state.truncated = True
    else:
        logger.info(
            "research_extract_start",
            request_id=state.request_id,
            stage="research",
            observations=len(state.raw_observations),
        )
        try:
            # 4. extract: 누적된 관찰에서 최종 WebFact를 만든다.
            state.extracted_facts = await _with_deadline(
                extract_facts(state),
                deadline=deadline,
                cap=_timeout_cap("RESEARCH_EXTRACT_TIMEOUT_S", 12.0),
            )
        except asyncio.TimeoutError:
            # fact 추출 LLM이 느릴 때도 observation에서 문장을 골라 fallback fact를 만든다.
            state.warnings.append("research_extract_timeout_fallback")
            state.extracted_facts = fallback_extract(state)
            if time.monotonic() >= deadline:
                state.truncated = True
                state.warnings.append("research_truncated")

    logger.info(
        "research_loop_done",
        request_id=state.request_id,
        stage="research",
        facts=len(state.extracted_facts),
        truncated=state.truncated,
        warnings=len(state.warnings),
        latency_ms=elapsed_ms(started),
    )
    return state
