"""Live Research에서 공유하는 상태와 데이터 모델.

이 파일은 "모듈 간 계약" 역할을 한다. 검색 도구, ReAct 루프, fact 추출기,
Strategy Agent 연결부가 모두 같은 Pydantic 모델을 사용해야 하므로 데이터
형태를 한 곳에 모아 둔다.

흐름 요약:
1. 도구는 `SearchResult`, `PageContent` 같은 원시 결과를 만든다.
2. graph는 원시 결과를 공통 형태인 `Observation`으로 누적한다.
3. extract_facts는 `Observation`에서 `WebFact`를 뽑는다.
4. api는 최종적으로 `ResearchResult`를 Strategy Agent에 반환한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.shared import Source, ToolName, WebFact


def utc_now_iso() -> str:
    """외부 관찰 결과의 fetch 시각을 UTC ISO 문자열로 통일한다."""
    return datetime.now(timezone.utc).isoformat()


class SearchResult(BaseModel):
    """웹 검색 결과 1개.

    검색 단계에서는 아직 페이지 본문을 읽지 않았기 때문에 `snippet`까지만
    신뢰할 수 있다. 이후 `fetch_page`가 같은 URL의 본문을 가져오면 더 강한
    evidence로 취급한다.
    """

    title: str = Field(min_length=1)
    url: HttpUrl
    snippet: str = Field(default="", max_length=1000)
    published_at: str | None = None


class PageContent(BaseModel):
    """화이트리스트를 통과한 웹페이지 본문 추출 결과."""

    url: HttpUrl
    title: str | None = None
    text: str
    published_at: str | None = None
    fetched_at: str = Field(default_factory=utc_now_iso)


class Observation(BaseModel):
    """ReAct 루프가 누적하는 공통 관찰 단위.

    서로 다른 도구 결과를 그대로 섞으면 extract 단계가 복잡해진다. 그래서
    검색/페이지/자막 결과를 모두 `Observation`으로 정규화하고, 원본 도구별
    세부 데이터는 `raw`에 보존한다.
    """

    tool: ToolName
    url: HttpUrl | None = None
    title: str | None = None
    text: str
    fetched_at: str = Field(default_factory=utc_now_iso)
    published_at: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ReActStep(BaseModel):
    """디버깅과 재현을 위한 ReAct trace 1단계."""

    step: int
    thought: str
    tool: ToolName
    tool_input: dict[str, Any]
    observation_summary: str = Field(max_length=500)


class PlanDecision(BaseModel):
    """plan 노드가 고른 다음 도구 호출."""

    thought: str = Field(default="", max_length=500)
    tool: ToolName
    tool_input: dict[str, Any] = Field(default_factory=dict)


class ReflectDecision(BaseModel):
    """reflect 노드가 판단한 '충분한 근거가 모였는가' 결과."""

    enough: bool
    reason: str = Field(default="", max_length=500)


class FactExtractionOut(BaseModel):
    """LLM structured output이 반환하는 fact 목록 wrapper."""

    facts: list[WebFact] = Field(default_factory=list, max_length=8)


class ResearchState(BaseModel):
    """Live Research 루프 내부에서 계속 갱신되는 전체 상태."""

    request_id: str
    patch_version: str
    question: str
    extracted_keywords: list[str] = Field(default_factory=list)

    react_log: list[ReActStep] = Field(default_factory=list)
    step: int = 0

    raw_observations: list[Observation] = Field(default_factory=list)
    extracted_facts: list[WebFact] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)

    domains_visited: list[str] = Field(default_factory=list)
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Strategy Agent에 반환하는 Live Research 최종 결과."""

    web_facts: list[WebFact] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    research_steps: int = 0
    domains_visited: list[str] = Field(default_factory=list)
    truncated: bool = False
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
