"""Observation에서 source-backed WebFact를 추출하는 단계.

우선순위:
1. LLM structured output으로 fact를 추출한다.
2. LLM이 없거나 실패하면 규칙 기반 fallback으로 문장을 골라 WebFact를 만든다.

핵심 안전장치:
- fact의 source_url은 반드시 실제 Observation 또는 검색 결과 URL이어야 한다.
- whitelist 밖 URL은 버린다.
- 단일 출처만 있을 때 confidence는 최대 0.7로 제한한다.
"""

from __future__ import annotations

import json
import os
import re
from urllib.parse import unquote, urlparse

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.strategy.llm import StrategyLLMError, call_structured
from app.research.state import FactExtractionOut, ResearchState
from app.research.whitelist import is_allowed_url_by_whitelist
from app.schemas.shared import WebFact


SYSTEM_PROMPT = """You are a fact extractor for Teamfight Tactics (TFT, also known as 롤토체스/롤체).
Your job is to extract accurate, source-backed facts from web observations to answer the user's TFT question.

## TFT Domain Context
TFT is an auto-battler game by Riot Games. Key concepts include:
- **챔피언/유닛(Champions/Units)**: Characters placed on the board. Each has a cost tier (1~5), traits, and abilities.
- **특성/시너지(Traits/Synergies)**: Bonuses activated when enough units sharing a trait are fielded.
- **아이템(Items)**: Equipment crafted from component combinations, equipped to champions.
- **증강(Augments)**: Powerful bonuses chosen during a game that modify playstyle.
- **덱/조합(Comps/Compositions)**: Specific team builds combining units, traits, items, and augments.
- **메타(Meta)**: The current strongest strategies and compositions in the game.
- **패치(Patch)**: Game updates that change champion stats, traits, items, and balance.
- **티어 리스트(Tier List)**: Rankings of comps/units/augments by strength (S > A > B > C > D).

## Extraction Rules
- Each fact must be 1-2 sentences and directly relevant to the user's question.
- Every fact MUST include a short direct quote (exact text) copied from the observation — do NOT paraphrase.
- Only use information explicitly present in the observations. Do NOT generate or infer data that is not in the provided text.
- Use only the current patch_version when the patch is explicitly mentioned.
- Do NOT invent numbers, win rates, pick rates, rankings, champion names, item names, or deck compositions.
- If the observation text is ambiguous or unclear, extract only the parts you are confident about.
- Prefer facts from official sources (patch notes, meta sites) over community posts.
- Return structured output only."""

# 명시적 패치 번호가 들어간 문장/URL을 검사하기 위한 정규식.
# 예: patch_version이 17.2인데 URL에 14.9가 있으면 stale evidence로 버린다.
PATCH_MENTION_RE = re.compile(r"(?<!\d)(\d{1,2}\.\d+[a-z]?)(?!\d)", re.IGNORECASE)

# 검색 결과에 자주 섞이는 사이트 소개/앱 홍보/오래된 공지 문구.
# 이런 문구는 사용자 질문에 직접 답하지 못하므로 fact 후보에서 제외한다.
BOILERPLATE_PATTERNS = (
    "전략적 팀 전투 tft 롤토체스 전적 검색 사이트",
    "lol tft stats, leaderboards",
    "teamfight tactics units data",
    "iphone, android, mobile, cheatsheet",
    "directx 9 지원 종료",
)


def _valid_source_urls(state: ResearchState) -> set[str]:
    """이번 research run에서 실제로 관찰한 URL 집합."""
    urls: set[str] = set()
    for obs in state.raw_observations:
        if obs.url:
            urls.add(str(obs.url).rstrip("/"))
        for result in obs.raw.get("results", []):
            url = str(result.get("url") or "").rstrip("/")
            if url:
                urls.add(url)
    return urls


def _serialize_observations(state: ResearchState) -> str:
    """LLM fact extractor에 넘길 관찰 데이터.

    페이지 본문은 길 수 있으므로 Observation당 3000자로 제한한다. 검색 결과도
    상위 5개만 넣어 토큰 폭주를 막는다.
    """
    observations = [
        {
            "tool": obs.tool,
            "url": str(obs.url) if obs.url else None,
            "title": obs.title,
            "published_at": obs.published_at,
            "text": obs.text[:3000],
            "results": obs.raw.get("results", [])[:5],
        }
        for obs in state.raw_observations
    ]
    return json.dumps(
        {
            "question": state.question,
            "patch_version": state.patch_version,
            "extracted_keywords": state.extracted_keywords,
            "observations": observations,
        },
        ensure_ascii=False,
        indent=2,
    )


def _terms(state: ResearchState) -> list[str]:
    """fallback scoring에 쓸 질문/키워드/패치 버전 토큰."""
    raw = " ".join([state.question, *state.extracted_keywords, state.patch_version])
    terms = re.findall(r"[A-Za-z0-9가-힣_.+-]{2,}", raw.lower())
    return list(dict.fromkeys(terms))


def _patch_base(version: str) -> str:
    """17.2b처럼 hotfix suffix가 붙은 버전을 17.2로 정규화한다."""
    return re.sub(r"[a-z]+$", "", version.lower())


def _mentions_wrong_patch(text: str, patch_version: str) -> bool:
    """현재 patch_version과 다른 명시적 패치 번호가 있으면 True."""
    if not re.match(r"^\d{1,2}\.\d+[a-z]?$", patch_version, re.IGNORECASE):
        return False
    current_base = _patch_base(patch_version)
    mentioned = PATCH_MENTION_RE.findall(unquote(text).lower())
    return any(_patch_base(version) != current_base for version in mentioned)


def _is_boilerplate(text: str) -> bool:
    """사이트 소개성 문구인지 확인한다."""
    lowered = text.lower()
    return any(pattern in lowered for pattern in BOILERPLATE_PATTERNS)


def _split_sentences(text: str) -> list[str]:
    """긴 본문을 fallback fact 후보 문장으로 나눈다."""
    chunks = [
        " ".join(part.split())
        for part in re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    ]
    chunks = [chunk for chunk in chunks if len(chunk) >= 20]
    if len(chunks) == 1 and len(chunks[0]) > 280:
        # 구두점이 거의 없는 HTML 추출문은 한 문장으로 붙어 나올 수 있다.
        # 이 경우 일정 길이로 잘라 최소한의 quote 후보를 만든다.
        long = chunks[0]
        chunks = [long[i:i + 260].strip() for i in range(0, len(long), 260)]
    return chunks


def _score_sentence(sentence: str, terms: list[str], patch_version: str) -> int:
    """fallback에서 어떤 문장이 질문과 더 관련 있는지 간단히 점수화한다."""
    lowered = sentence.lower()
    score = 0
    if patch_version in sentence:
        score += 3
    if "tft" in lowered or "teamfight" in lowered:
        score += 1
    for term in terms:
        if term in lowered:
            score += 1
    return score


def _fact_from_text(
    *,
    source_url: str,
    title: str | None,
    published_at: str | None,
    text: str,
    terms: list[str],
    patch_version: str,
) -> WebFact | None:
    """본문/스니펫 하나에서 가장 관련 있는 문장을 골라 WebFact를 만든다."""
    source_context = " ".join([source_url, title or "", text[:500]])
    if _mentions_wrong_patch(source_context, patch_version):
        return None

    sentences = _split_sentences(text)
    if not sentences:
        return None
    ranked = sorted(
        [sentence for sentence in sentences if not _is_boilerplate(sentence)],
        key=lambda s: _score_sentence(s, terms, patch_version),
        reverse=True,
    )
    if not ranked:
        return None
    best = ranked[0]
    if _score_sentence(best, terms, patch_version) <= 0:
        best = sentences[0]

    domain = urlparse(source_url).netloc
    confidence = 0.65
    if patch_version in best:
        confidence += 0.1
    parsed_domain = urlparse(source_url).netloc.lower()
    if "teamfighttactics.leagueoflegends.com" in parsed_domain:
        confidence += 0.1
    if domain:
        # fallback confidence는 과신하지 않는다. 여러 출처 합의 없이 추출한
        # 단일 문장이므로 공식 출처라도 0.85까지만 허용한다.
        confidence = min(confidence, 0.85)

    try:
        return WebFact(
            text=best[:400],
            quote=best[:300],
            source_url=source_url,
            source_title=title,
            published_at=published_at,
            extraction_confidence=confidence,
        )
    except ValidationError:
        # Pydantic 제약(HttpUrl, 길이, confidence 범위 등)을 통과하지 못하면 버린다.
        return None


def _fallback_extract(state: ResearchState) -> list[WebFact]:
    """LLM이 없을 때 Observation에서 WebFact를 만드는 규칙 기반 extractor."""
    terms = _terms(state)
    facts: list[WebFact] = []
    seen: set[tuple[str, str]] = set()

    for obs in state.raw_observations:
        if obs.url:
            # fetch_page처럼 URL이 있는 Observation은 검색 snippet보다
            # 신뢰도가 높으므로 먼저 fact 후보로 본다.
            fact = _fact_from_text(
                source_url=str(obs.url),
                title=obs.title,
                published_at=obs.published_at,
                text=obs.text,
                terms=terms,
                patch_version=state.patch_version,
            )
            if fact:
                key = (str(fact.source_url).rstrip("/"), fact.text.lower())
                if key not in seen:
                    facts.append(fact)
                    seen.add(key)

        for result in obs.raw.get("results", []):
            # 검색만 성공하고 페이지 fetch가 실패한 경우도 있다. 이때는 snippet을
            # 낮은 confidence의 fallback evidence로 사용한다.
            url = str(result.get("url") or "")
            snippet = str(result.get("snippet") or "")
            if not url or not snippet:
                continue
            fact = _fact_from_text(
                source_url=url,
                title=str(result.get("title") or "") or None,
                published_at=result.get("published_at"),
                text=snippet,
                terms=terms,
                patch_version=state.patch_version,
            )
            if fact:
                key = (str(fact.source_url).rstrip("/"), fact.text.lower())
                if key not in seen:
                    facts.append(fact)
                    seen.add(key)

        if len(facts) >= 5:
            break

    return _cap_single_source_confidence(facts[:5])


def fallback_extract(state: ResearchState) -> list[WebFact]:
    """graph의 timeout fallback에서 직접 호출할 수 있도록 노출한 wrapper."""
    return _fallback_extract(state)


def _llm_extractor_enabled() -> bool:
    """LLM extractor는 명시적으로 켰을 때만 사용한다.

    기본 Live Research는 관찰한 웹 문서와 검색 snippet에서 deterministic fact를
    추출해 요청 시간을 예측 가능하게 유지한다.
    """
    return os.getenv("RESEARCH_LLM_EXTRACT_ENABLED", "false").lower() == "true"


def _cap_single_source_confidence(facts: list[WebFact]) -> list[WebFact]:
    """출처가 하나뿐이면 confidence를 제한한다."""
    distinct_sources = {str(f.source_url).rstrip("/") for f in facts}
    if len(distinct_sources) <= 1:
        for fact in facts:
            fact.extraction_confidence = min(fact.extraction_confidence, 0.7)
    return facts


def _sanitize_facts(state: ResearchState, facts: list[WebFact]) -> list[WebFact]:
    """LLM이 만든 fact를 deterministic guard로 검증한다."""
    valid_urls = _valid_source_urls(state)
    out: list[WebFact] = []
    seen: set[tuple[str, str]] = set()
    for fact in facts:
        url = str(fact.source_url).rstrip("/")
        if url not in valid_urls or not is_allowed_url_by_whitelist(url):
            # LLM이 관찰하지 않은 URL을 만들거나 whitelist 밖 URL을 내면 제거한다.
            continue
        context = " ".join([url, fact.source_title or "", fact.text, fact.quote])
        if _mentions_wrong_patch(context, state.patch_version) or _is_boilerplate(fact.text):
            continue
        key = (url, fact.text.lower())
        if key in seen:
            continue
        fact.text = fact.text[:400]
        fact.quote = fact.quote[:300]
        out.append(fact)
        seen.add(key)
        if len(out) >= 5:
            break
    return _cap_single_source_confidence(out)


async def extract_facts(state: ResearchState) -> list[WebFact]:
    """누적 Observation에서 최종 WebFact 목록을 추출한다."""
    if not state.raw_observations:
        return []
    if not _llm_extractor_enabled():
        return _fallback_extract(state)

    try:
        # LLM extractor는 quote/source를 함께 반환하도록 schema로 강제한다.
        result = await call_structured(
            role="research",
            schema=FactExtractionOut,
            messages=[
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_serialize_observations(state)),
            ],
            retries=1,
        )
        facts = _sanitize_facts(state, result.facts)
        if facts:
            return facts
    except StrategyLLMError:
        pass

    # LLM이 없거나 유효한 fact를 만들지 못하면 규칙 기반 추출로 degrade한다.
    return _fallback_extract(state)
