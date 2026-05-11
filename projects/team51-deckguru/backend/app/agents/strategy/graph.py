"""LangGraph StateGraph — 02-spec §3 super-graph.

흐름:
  START → analyze_intent
    ├─ intent=other ──────────────────────────────────────────► format_response → END
    └─ otherwise → rag_retrieve → need_live? ──┬─ live → live_research ─┐
                                                └─ skip ─────────────────┴─► analyze_meta
                                                  → recommend → verify_grounding → format_response → END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.strategy.nodes.analyze_intent import analyze_intent
from app.agents.strategy.nodes.analyze_meta import analyze_meta
from app.agents.strategy.nodes.format_response import format_response_node
from app.agents.strategy.nodes.live_research import live_research
from app.agents.strategy.nodes.need_live import need_live_branch
from app.agents.strategy.nodes.rag_retrieve import rag_retrieve
from app.agents.strategy.nodes.recommend import recommend
from app.agents.strategy.nodes.verify_grounding import verify_grounding
from app.agents.strategy.state import StrategyState


def _intent_branch(state: StrategyState) -> str:
    return "other" if state.intent == "other" else "continue"


def build_graph() -> Any:
    """StateGraph 컴파일.

    노드는 모두 async 또는 sync 순수 함수. LangGraph는 Pydantic state를
    그대로 받아 dict로 변환 후 다음 노드에 전달. 여기서는 모든 노드가
    StrategyState를 in/out으로 받도록 통일.
    """
    g: StateGraph = StateGraph(StrategyState)

    g.add_node("analyze_intent", analyze_intent)
    g.add_node("rag_retrieve", rag_retrieve)
    g.add_node("live_research", live_research)
    g.add_node("analyze_meta", analyze_meta)
    g.add_node("recommend", recommend)
    g.add_node("verify_grounding", verify_grounding)
    g.add_node("format_response", format_response_node)

    g.add_edge(START, "analyze_intent")

    # intent=other → format_response 직행
    g.add_conditional_edges(
        "analyze_intent",
        _intent_branch,
        {
            "other": "format_response",
            "continue": "rag_retrieve",
        },
    )

    # need_live? 조건부 분기
    g.add_conditional_edges(
        "rag_retrieve",
        need_live_branch,
        {
            "live": "live_research",
            "skip": "analyze_meta",
        },
    )
    g.add_edge("live_research", "analyze_meta")

    g.add_edge("analyze_meta", "recommend")
    g.add_edge("recommend", "verify_grounding")
    g.add_edge("verify_grounding", "format_response")
    g.add_edge("format_response", END)

    return g.compile()


# 앱 부팅 시 1회 컴파일 (LangGraph 내부 캐시).
COMPILED_GRAPH = build_graph()
