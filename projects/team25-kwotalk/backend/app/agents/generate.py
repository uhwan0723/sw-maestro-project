"""generate_node — 검색·가이드·합의금을 모아 답변 생성 (스트리밍 지원)."""
import logging
from collections.abc import AsyncIterator

from app.constants import DISCLAIMER, MAX_CONTEXT_DOCS, MAX_HISTORY_TURNS
from app.llm.solar_client import SolarAPIError, call_pro_stream
from app.state import LegalState, RetrievedDoc
from app.taxonomy import CASE_TYPE_KOREAN
from app.utils.citation_extractor import extract_citations
from app.utils.prompt_loader import fill_template, load_prompt

logger = logging.getLogger(__name__)


def _build_retrieved_docs_block(docs: list[RetrievedDoc]) -> str:
    if not docs:
        return "(검색된 자료 없음)"
    lines = []
    for i, doc in enumerate(docs, start=1):
        lines.append(f"[{i}] {doc['title']}")
        lines.append(doc["content"])
        lines.append("")
    return "\n".join(lines).strip()


def _build_guide_block(guide_steps: list[str] | None) -> str:
    if not guide_steps:
        return "(해당 없음)"
    return "\n".join(f"{i}. {step}" for i, step in enumerate(guide_steps, start=1))


def _build_settlement_block(settlement) -> str:
    if settlement is None:
        return "(해당 없음)"
    return (
        f"유사 사례 {settlement['sample_size']}건 기반: "
        f"최소 {settlement['min']:,}원 / 중간값 {settlement['median']:,}원 / 최대 {settlement['max']:,}원\n"
        f"산출 근거: {settlement['basis']}"
    )


def _build_history_block(history, max_turns: int) -> str:
    if not history:
        return "(없음)"
    recent = history[-max_turns:]
    return "\n".join(f"[{m['role']}] {m['content']}" for m in recent)


def _build_fallback_answer(docs: list[RetrievedDoc]) -> str:
    lines = ["현재 AI 답변 생성에 일시적 문제가 있어 관련 자료를 안내드립니다.\n"]
    for i, doc in enumerate(docs, start=1):
        summary = doc["content"][:120].replace("\n", " ")
        lines.append(f"[{i}] **{doc['title']}**\n{summary}...\n")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _prepare_context(state: LegalState):
    case_type = state.get("case_type") or "OUT_OF_SCOPE"
    case_type_korean = CASE_TYPE_KOREAN.get(case_type, case_type)

    all_docs: list[RetrievedDoc] = state.get("retrieved_docs") or []
    sorted_docs = sorted(all_docs, key=lambda d: d["score"], reverse=True)[:MAX_CONTEXT_DOCS]

    guide_steps = state.get("guide_steps")
    settlement = state.get("settlement")
    history = state.get("history") or []

    return case_type_korean, sorted_docs, guide_steps, settlement, history


async def generate_node(state: LegalState) -> dict:
    """반환: {answer_text, citations}. 토큰 누적 후 인용 추출."""
    case_type_korean, docs, guide_steps, settlement, history = _prepare_context(state)

    system_prompt = load_prompt("generate_system.txt")
    user_template = load_prompt("generate_user_template.txt")
    user_prompt = fill_template(
        user_template,
        case_type_korean=case_type_korean,
        retrieved_docs_block=_build_retrieved_docs_block(docs),
        guide_block=_build_guide_block(guide_steps),
        settlement_block=_build_settlement_block(settlement),
        history_block=_build_history_block(history, MAX_HISTORY_TURNS),
        user_query=state["user_query"],
    )

    try:
        stream = await call_pro_stream(system_prompt=system_prompt, user_prompt=user_prompt)
        tokens = []
        async for token in stream:
            tokens.append(token)
        answer_text = "".join(tokens)
    except SolarAPIError as exc:
        logger.warning("Solar Pro 실패, 폴백 답변 사용: %s", exc)
        answer_text = _build_fallback_answer(docs)

    if DISCLAIMER not in answer_text:
        answer_text = answer_text.rstrip() + "\n\n" + DISCLAIMER

    citations = extract_citations(answer_text, docs)
    return {"answer_text": answer_text, "citations": citations}


async def generate_node_stream(state: LegalState) -> AsyncIterator[str]:
    """LangGraph astream_events 연동을 위한 토큰 단위 yield 버전."""
    case_type_korean, docs, guide_steps, settlement, history = _prepare_context(state)

    system_prompt = load_prompt("generate_system.txt")
    user_template = load_prompt("generate_user_template.txt")
    user_prompt = fill_template(
        user_template,
        case_type_korean=case_type_korean,
        retrieved_docs_block=_build_retrieved_docs_block(docs),
        guide_block=_build_guide_block(guide_steps),
        settlement_block=_build_settlement_block(settlement),
        history_block=_build_history_block(history, MAX_HISTORY_TURNS),
        user_query=state["user_query"],
    )

    try:
        stream = await call_pro_stream(system_prompt=system_prompt, user_prompt=user_prompt)
        accumulated = []
        async for token in stream:
            accumulated.append(token)
            yield token

        full_text = "".join(accumulated)
        if DISCLAIMER not in full_text:
            yield "\n\n" + DISCLAIMER
    except SolarAPIError as exc:
        logger.warning("Solar Pro 스트리밍 실패: %s", exc)
        yield _build_fallback_answer(docs)
