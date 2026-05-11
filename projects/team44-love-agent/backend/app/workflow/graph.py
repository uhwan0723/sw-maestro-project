from __future__ import annotations

import asyncio
from typing import Any

from app.services.event_broker import EventBroker
from app.services.llm_client import LLMClient
from app.store.memory import MemoryStore
from app.workflow.classification import should_skip_to_final
from app.workflow.nodes import WorkflowNodes, WorkflowTimeoutError
from app.workflow.state import ConsultationGraphState


WORKFLOW_TIMEOUT_SECONDS = 300.0


class WorkflowRunner:
    def __init__(self, store: MemoryStore, broker: EventBroker, llm: LLMClient) -> None:
        self.nodes = WorkflowNodes(store, broker, llm)
        self.graph = build_consultation_graph(self.nodes)

    async def run(self, consultation_id: str, initial_state: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(
                self.graph.ainvoke(initial_state),
                timeout=WORKFLOW_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            await self.nodes.handle_failure(
                consultation_id, WorkflowTimeoutError(WORKFLOW_TIMEOUT_SECONDS)
            )
        except Exception as exc:
            await self.nodes.handle_failure(consultation_id, exc)


def build_consultation_graph(nodes: WorkflowNodes):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return SequentialConsultationGraph(nodes)

    graph = StateGraph(ConsultationGraphState)
    graph.add_node("analyze_question", nodes.analyze_question)
    graph.add_node("run_round_1", nodes.run_round_1)
    graph.add_node("summarize_round_1", nodes.summarize_round_1)
    graph.add_node("run_round_2", nodes.run_round_2)
    graph.add_node("classify_round_2", nodes.classify_round_2)
    graph.add_node("mark_consensus_reached", nodes.mark_consensus_reached)
    graph.add_node("run_round_3", nodes.run_round_3)
    graph.add_node("finalize", nodes.finalize)

    graph.add_edge(START, "analyze_question")
    graph.add_edge("analyze_question", "run_round_1")
    graph.add_edge("run_round_1", "summarize_round_1")
    graph.add_edge("summarize_round_1", "run_round_2")
    graph.add_edge("run_round_2", "classify_round_2")
    graph.add_conditional_edges(
        "classify_round_2",
        _route_after_classify,
        {
            "skip_to_final": "mark_consensus_reached",
            "proceed_to_round_3": "run_round_3",
        },
    )
    graph.add_edge("mark_consensus_reached", "finalize")
    graph.add_edge("run_round_3", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _route_after_classify(state: ConsultationGraphState) -> str:
    classify_2 = state.get("classify_2") or {}
    payload = classify_2.get("payload") or {}
    if should_skip_to_final(payload):
        return "skip_to_final"
    return "proceed_to_round_3"


class SequentialConsultationGraph:
    """Fallback runner used only when langgraph is unavailable locally."""

    def __init__(self, nodes: WorkflowNodes) -> None:
        self._nodes = nodes

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        working = dict(state)
        for step in [
            self._nodes.analyze_question,
            self._nodes.run_round_1,
            self._nodes.summarize_round_1,
            self._nodes.run_round_2,
            self._nodes.classify_round_2,
        ]:
            working.update(await step(working))
        if _route_after_classify(working) == "skip_to_final":
            working.update(await self._nodes.mark_consensus_reached(working))
        else:
            working.update(await self._nodes.run_round_3(working))
        working.update(await self._nodes.finalize(working))
        return working
