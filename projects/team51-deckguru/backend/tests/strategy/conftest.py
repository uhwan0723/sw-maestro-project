"""Test fixtures + Upstage LLM mock.

`call_structured`를 monkeypatch해서 LLM 호출 없이 graph 흐름을 검증.
실제 LLM 통합 테스트는 `tests/test_strategy_live.py` (UPSTAGE_API_KEY 필요).
"""

from __future__ import annotations

import pytest

from app.schemas.shared import DeckDraft, DeckRecommendation, PlaybookStep


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.setenv("PATCH_VERSION", "14.9")
    monkeypatch.setenv("LIVE_RESEARCH_ENABLED", "false")
    monkeypatch.setenv("DEMO_MODE", "false")
    from app.agents.strategy.nodes import rag_retrieve as rr_mod
    from app.agents.strategy.nodes import verify_grounding as vg_mod
    from app.rag.testing import InMemoryStubRagService

    stub = InMemoryStubRagService()
    monkeypatch.setattr(rr_mod, "get_rag_service", lambda: stub)
    monkeypatch.setattr(vg_mod, "get_rag_service", lambda: stub)


def _intent_stub(question: str):
    from app.agents.strategy.nodes.analyze_intent import IntentOut
    if "운영법" in question:
        return IntentOut(intent="deck_playstyle", extracted_keywords=["정밀 리롤"])
    if "곡궁" in question or "BF" in question:
        return IntentOut(intent="item_pivot", extracted_keywords=["곡궁"])
    if "패치" in question and "요약" in question:
        return IntentOut(intent="patch_summary", extracted_keywords=["14.9", "패치 노트"])
    if "회원가입" in question or "날씨" in question:
        return IntentOut(intent="other", extracted_keywords=[])
    return IntentOut(intent="recommend_deck", extracted_keywords=["골드", "티어"])


def _meta_stub():
    from app.agents.strategy.nodes.analyze_meta import MetaOut
    return MetaOut(
        meta_summary="14.9 패치는 정밀 시너지 버프와 사이버시티 챔피언 너프가 핵심. 정밀 리롤 덱이 안정적이며, 사이버시티 9코는 고점은 높으나 난이도 상승.",
        candidate_decks=[
            DeckDraft(
                name="정밀 리롤",
                difficulty="easy",
                core_units=["정밀의 사도", "기계 학자", "광신도", "라이트브링어"],
                key_items=["구인수의 격노검", "최후의 속삭임", "정의의 손"],
                evidence_chunk_ids=["d_jeongmil_reroll_14.9"],
            ),
            DeckDraft(
                name="사이버시티 9코",
                difficulty="hard",
                core_units=["사이버시티 챔피언", "9코스트 정밀", "어둠의 화신"],
                key_items=["구인수의 격노검", "거인 학살자"],
                evidence_chunk_ids=["d_cyber_14.9"],
            ),
        ],
    )


def _recommend_stub():
    from app.agents.strategy.nodes.recommend import RecommendOut
    return RecommendOut(
        decks=[
            DeckRecommendation(
                name="정밀 리롤",
                difficulty="easy",
                core_units=["정밀의 사도", "기계 학자", "광신도", "라이트브링어"],
                key_items=["구인수의 격노검", "최후의 속삭임", "정의의 손"],
                augment_direction="정밀 시너지를 강화하는 silver/gold augment 우선",
                playbook=[
                    PlaybookStep(phase="early", instruction="2-1 50골드 경제 빌드, 4레벨 도달 후 안정화"),
                    PlaybookStep(phase="mid", instruction="6레벨에서 정밀의 사도 3성 시도, 기계 학자 시너지 활성화"),
                    PlaybookStep(phase="late", instruction="8레벨 도달 후 광신도 추가, 아이템 풀 분배"),
                ],
                good_conditions=["BF대검 또는 곡궁이 초반에 풀릴 때", "광신도가 자주 떴을 때"],
                avoid_conditions=["다른 정밀 유저가 2명 이상일 때"],
                fallback_plan="정밀 풀이 좁으면 라이트브링어 캐리로 전환",
                rationale="현재 자료 기준 정밀 리롤은 안정적인 평균 등수를 보여주며, 골드 티어에서 운영 난이도가 낮은 편.",
            ),
        ],
    )


@pytest.fixture
def mock_llm(monkeypatch):
    """analyze_intent / analyze_meta / recommend 의 call_structured를 모킹."""

    async def fake_intent(role, schema, messages, retries=1):
        question = messages[-1].content
        return _intent_stub(question)

    async def fake_meta(role, schema, messages, retries=1):
        return _meta_stub()

    async def fake_recommend(role, schema, messages, retries=1):
        return _recommend_stub()

    # 노드별 모듈에 imported된 call_structured를 각각 패치
    from app.agents.strategy.nodes import analyze_intent as ai_mod
    from app.agents.strategy.nodes import analyze_meta as am_mod
    from app.agents.strategy.nodes import recommend as rc_mod

    monkeypatch.setattr(ai_mod, "call_structured", fake_intent)
    monkeypatch.setattr(am_mod, "call_structured", fake_meta)
    monkeypatch.setattr(rc_mod, "call_structured", fake_recommend)
    return None
