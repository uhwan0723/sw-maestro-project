"""ReAct의 plan 단계.

역할:
- 현재 질문과 지금까지의 Observation을 보고 다음에 부를 도구 하나를 고른다.
- LLM이 가능하면 structured output으로 `PlanDecision`을 받는다.
- LLM/API 키가 없거나 schema가 깨지면 `_fallback_plan()`으로 결정한다.

fallback 전략:
1. 질문 안에 URL이 있으면 그 URL부터 확인한다.
2. 이전 web_search 결과 중 아직 fetch하지 않은 URL을 fetch한다.
3. 확인할 URL이 없으면 DuckDuckGo 검색을 한다.
"""

from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.strategy.llm import StrategyLLMError, call_structured
from app.research.state import PlanDecision, ResearchState
from app.research.whitelist import is_allowed_url_by_whitelist


URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
# patch_version이 "current"처럼 추상값이면 stale한 숫자 패치를 검색어에 넣지 않는다.
# 숫자 버전일 때만 "patch 14.9" 같은 명시 검색어를 만든다.
PATCH_VERSION_RE = re.compile(r"^\d{1,2}\.\d+[a-z]?$", re.IGNORECASE)

# 사용자가 메타 덱 추천을 묻는지 판단하기 위한 최소 키워드 목록.
# LLM planner가 timeout/fail일 때도 deterministic fallback이 의도를 놓치지 않게 둔다.
META_DECK_KEYWORDS = (
    "덱",
    "텍",  # common typo for "덱" in quick manual tests
    "메타",
    "조합",
    "추천",
    "좋은",
    "best",
    "deck",
    "comps",
    "meta",
)

# 검색엔진이 단순 패치노트만 반환하지 않도록 메타 사이트와 "comps/tier list"
# 의도를 query에 강하게 섞는다.
META_DECK_QUERY_HINT = (
    "best meta comps tier list 추천 덱 조합 "
    "site:metatft.com OR site:lolchess.gg OR site:tactics.tools"
)


SYSTEM_PROMPT = """You are DeckGuru's TFT live researcher.
Choose exactly one tool call that can collect current, source-backed facts.

Available tools:
- web_search(query: str, k: int = 5)
- fetch_page(url: str)

Rules:
- Prefer official patch notes or whitelisted meta sites.
- Do not repeat the same tool input.
- Return only structured output."""


def _visited_urls(state: ResearchState) -> set[str]:
    """이미 관찰했거나 호출했던 URL/영상 ID를 모아 반복 호출을 막는다."""
    urls = {str(obs.url) for obs in state.raw_observations if obs.url}
    for step in state.react_log:
        value = step.tool_input.get("url") or step.tool_input.get("video_id")
        if value:
            urls.add(str(value))
    return urls


def _is_meta_deck_query(state: ResearchState) -> bool:
    """질문이 '좋은 메타 덱/조합 추천' 유형인지 대략 판별한다."""
    blob = " ".join([state.question, *state.extracted_keywords]).lower()
    return any(keyword in blob for keyword in META_DECK_KEYWORDS)


def _url_priority(url: str, state: ResearchState) -> int:
    """검색 결과 URL의 fetch 우선순위.

    메타 덱 질문은 comps/meta 페이지가 가장 중요하다. patch note나 unit tier list는
    보조 근거일 뿐이므로 뒤로 보낸다.
    """
    lowered = url.lower()
    if not _is_meta_deck_query(state):
        if "teamfighttactics.leagueoflegends.com" in lowered and "/game-updates/" in lowered:
            return 100
        if "teamfighttactics.leagueoflegends.com" in lowered:
            return 80
        return 50

    if "metatft.com/comps" in lowered:
        return 120
    if "lolchess.gg/meta" in lowered:
        return 115
    if "tactics.tools/team-compositions" in lowered:
        return 110
    if "metatft.com" in lowered and "units" not in lowered:
        return 80
    if "lolchess.gg" in lowered and "patch" not in lowered:
        return 75
    if "teamfighttactics.leagueoflegends.com" in lowered and "/game-updates/" in lowered:
        return 50
    if "units" in lowered or "champion" in lowered:
        return 10
    if "patch" in lowered:
        return 20
    return 40


def _search_result_urls(state: ResearchState) -> list[str]:
    """검색 Observation의 raw 결과에서 아직 fetch하지 않은 whitelist URL을 꺼낸다."""
    urls: list[str] = []
    seen = _visited_urls(state)
    for obs in state.raw_observations:
        for result in obs.raw.get("results", []):
            url = str(result.get("url") or "")
            if url and url not in seen and is_allowed_url_by_whitelist(url):
                urls.append(url)
                seen.add(url)
    return sorted(urls, key=lambda url: _url_priority(url, state), reverse=True)


def _first_allowed_question_url(state: ResearchState) -> str | None:
    """사용자 질문에 직접 포함된 URL 중 우선 처리할 URL을 찾는다."""
    for match in URL_RE.findall(state.question):
        url = match.rstrip(".,")
        if is_allowed_url_by_whitelist(url) and url not in _visited_urls(state):
            return url
    return None


def _default_query(state: ResearchState) -> str:
    """검색 query의 기본 골격을 만든다."""
    patch_part = (
        f"patch {state.patch_version}"
        if PATCH_VERSION_RE.match(state.patch_version)
        else "current patch"
    )
    parts = ["TFT", patch_part, state.question]
    parts.extend(state.extracted_keywords)
    if _is_meta_deck_query(state):
        parts.append(META_DECK_QUERY_HINT)
    return " ".join(part for part in parts if part).strip()[:300]


def _fallback_plan(state: ResearchState) -> PlanDecision:
    """LLM plan이 실패했을 때 쓰는 deterministic planner."""
    question_url = _first_allowed_question_url(state)
    if question_url:
        return PlanDecision(
            thought="Question includes a whitelisted URL; fetch it directly.",
            tool="fetch_page",
            tool_input={"url": question_url},
        )

    for url in _search_result_urls(state):
        # 검색으로 URL을 찾았다면 다음 step은 본문 fetch가 우선이다. snippet만으로
        # fact를 만들 수도 있지만, 본문까지 읽은 fact가 grounding에 더 유리하다.
        return PlanDecision(
            thought="Fetch the strongest whitelisted search result.",
            tool="fetch_page",
            tool_input={"url": url},
        )

    suffixes = [
        "",
        " MetaTFT comps lolchess meta",
        " site:metatft.com/comps OR site:lolchess.gg/meta",
        " lolchess tactics.tools metatft",
    ]
    suffix = suffixes[min(len(state.react_log), len(suffixes) - 1)]
    # 같은 검색어를 반복하면 같은 결과만 나올 가능성이 높다. step이 늘수록
    # official/meta site 쪽으로 query를 조금씩 좁혀 다른 결과를 유도한다.
    return PlanDecision(
        thought="Search current whitelisted sources for fresh TFT facts.",
        tool="web_search",
        tool_input={"query": f"{_default_query(state)}{suffix}", "k": 5},
    )


def fallback_plan(state: ResearchState) -> PlanDecision:
    """graph의 timeout fallback에서 직접 호출할 수 있도록 노출한 wrapper."""
    return _fallback_plan(state)


def _llm_planner_enabled() -> bool:
    """LLM planner는 명시적으로 켰을 때만 사용한다.

    Live Research의 핵심은 외부 출처 확인이다. 기본 경로에서는 제한된 요청
    예산을 structured planning LLM보다 검색/fetch에 우선 배정한다.
    """
    return os.getenv("RESEARCH_LLM_PLANNER_ENABLED", "false").lower() == "true"


def _state_summary(state: ResearchState) -> str:
    """LLM planner에 넘길 최소 상태 요약.

    전체 본문을 넣으면 토큰이 커지므로 최근 Observation만 500자씩 잘라 보낸다.
    """
    observations = [
        {
            "tool": obs.tool,
            "url": str(obs.url) if obs.url else None,
            "title": obs.title,
            "text": obs.text[:500],
        }
        for obs in state.raw_observations[-5:]
    ]
    return json.dumps(
        {
            "patch_version": state.patch_version,
            "question": state.question,
            "extracted_keywords": state.extracted_keywords,
            "observations": observations,
            "previous_steps": [s.model_dump(mode="json") for s in state.react_log],
        },
        ensure_ascii=False,
        indent=2,
    )


async def plan_next_action(state: ResearchState) -> PlanDecision:
    if not _llm_planner_enabled():
        return _fallback_plan(state)

    try:
        result = await call_structured(
            role="research",
            schema=PlanDecision,
            messages=[
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_state_summary(state)),
            ],
            retries=1,
        )
    except StrategyLLMError:
        return _fallback_plan(state)

    # LLM이 structured schema를 지켜도 tool_input 내용이 비어 있거나 whitelist를
    # 벗어날 수 있다. 실행 직전 한 번 더 deterministic guard를 둔다.
    if result.tool == "fetch_page":
        url = str(result.tool_input.get("url") or "")
        if not url or not is_allowed_url_by_whitelist(url):
            return _fallback_plan(state)
    elif result.tool == "web_search":
        query = str(result.tool_input.get("query") or "").strip()
        if not query:
            return _fallback_plan(state)

    return result
