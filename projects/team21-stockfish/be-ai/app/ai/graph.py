from collections.abc import Mapping
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.ai.compose_report import compose_report
from app.ai.explain_term import explain_term
from app.ai.generate_hypotheses import generate_hypotheses
from app.ai.load_context import load_context
from app.ai.route_request import route_request
from app.ai.safety_check import safety_check
from app.ai.safety_review import safety_review
from app.ai.state import AgentState
from app.ai.verify_hypotheses import verify_hypotheses
from app.models.enums import RequestType


SAFETY_CHECK_NODE = "safety_check"
ROUTE_REQUEST_NODE = "route_request"
LOAD_CONTEXT_NODE = "load_context"
GENERATE_HYPOTHESES_NODE = "generate_hypotheses"
VERIFY_HYPOTHESES_NODE = "verify_hypotheses"
COMPOSE_REPORT_NODE = "compose_report"
EXPLAIN_TERM_NODE = "explain_term"
SAFETY_REVIEW_NODE = "safety_review"

RouteAfterSafetyCheck = Literal[
    "route_request",
    "sector_analysis",
    "end",
]
RouteAfterRequest = Literal["sector_analysis", "term_explanation", "end"]


def build_agent_graph() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node(SAFETY_CHECK_NODE, safety_check)
    workflow.add_node(ROUTE_REQUEST_NODE, route_request)
    workflow.add_node(LOAD_CONTEXT_NODE, load_context)
    workflow.add_node(GENERATE_HYPOTHESES_NODE, generate_hypotheses)
    workflow.add_node(VERIFY_HYPOTHESES_NODE, verify_hypotheses)
    workflow.add_node(COMPOSE_REPORT_NODE, compose_report)
    workflow.add_node(EXPLAIN_TERM_NODE, explain_term)
    workflow.add_node(SAFETY_REVIEW_NODE, safety_review)

    workflow.add_edge(START, SAFETY_CHECK_NODE)
    workflow.add_conditional_edges(
        SAFETY_CHECK_NODE,
        _route_after_safety_check,
        {
            "route_request": ROUTE_REQUEST_NODE,
            "sector_analysis": LOAD_CONTEXT_NODE,
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        ROUTE_REQUEST_NODE,
        _route_after_request,
        {
            "sector_analysis": LOAD_CONTEXT_NODE,
            "term_explanation": EXPLAIN_TERM_NODE,
            "end": END,
        },
    )
    workflow.add_edge(LOAD_CONTEXT_NODE, GENERATE_HYPOTHESES_NODE)
    workflow.add_edge(GENERATE_HYPOTHESES_NODE, VERIFY_HYPOTHESES_NODE)
    workflow.add_edge(VERIFY_HYPOTHESES_NODE, COMPOSE_REPORT_NODE)
    workflow.add_edge(COMPOSE_REPORT_NODE, SAFETY_REVIEW_NODE)
    workflow.add_edge(EXPLAIN_TERM_NODE, SAFETY_REVIEW_NODE)
    workflow.add_edge(SAFETY_REVIEW_NODE, END)

    return workflow.compile()


def _route_after_safety_check(
    state: AgentState | Mapping[str, Any],
) -> RouteAfterSafetyCheck:
    if _has_final_answer(state):
        return "end"

    request_type = _read_request_type(state)
    if request_type is RequestType.SECTOR_ANALYSIS:
        return "sector_analysis"

    return "route_request"


def _route_after_request(
    state: AgentState | Mapping[str, Any],
) -> RouteAfterRequest:
    if _has_final_answer(state):
        return "end"

    request_type = _read_request_type(state)
    if request_type is RequestType.SECTOR_ANALYSIS:
        return "sector_analysis"
    if request_type is RequestType.TERM_EXPLANATION:
        return "term_explanation"
    return "end"


def _has_final_answer(state: AgentState | Mapping[str, Any]) -> bool:
    if isinstance(state, AgentState):
        return state.final_answer is not None

    value = state.get("final_answer")
    return isinstance(value, str) and bool(value)


def _read_request_type(state: AgentState | Mapping[str, Any]) -> RequestType | None:
    if isinstance(state, AgentState):
        return state.request_type

    value = state.get("request_type")
    if isinstance(value, RequestType):
        return value
    if isinstance(value, str):
        try:
            return RequestType(value)
        except ValueError:
            return None
    return None


agent_graph = build_agent_graph()


async def run_agent(state: AgentState | Mapping[str, Any]) -> AgentState:
    payload = state.to_graph_payload() if isinstance(state, AgentState) else dict(state)
    result = await agent_graph.ainvoke(payload)
    return AgentState.model_validate(result)
