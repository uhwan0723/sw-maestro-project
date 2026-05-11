from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from performation_agent.nodes import (
  analyze_input,
  assign_confidence,
  build_search_queries,
  classify_sources,
  extract_event_info,
  format_response,
  infer_event_candidates,
  infer_venue_from_search,
  load_venue_data,
  search_kopis_official,
  search_public_web,
  summarize_information,
)
from performation_agent.state import GuideState
from performation_domain import GuideResponse


NODE_SEQUENCE = (
  "analyze_input",
  "load_venue_data",
  "build_search_queries",
  "search_public_web",
  "search_kopis_official",
  "infer_venue_from_search",
  "infer_event_candidates",
  "extract_event_info",
  "classify_sources",
  "summarize_information",
  "assign_confidence",
  "format_response",
)


def generate_visit_guide(query: str) -> GuideResponse:
  state = build_workflow_graph().invoke({"query": query})
  return state["response"]


@lru_cache(maxsize=1)
def build_workflow_graph():
  graph = StateGraph(GuideState)
  graph.add_node("analyze_input", analyze_input)
  graph.add_node("load_venue_data", load_venue_data)
  graph.add_node("build_search_queries", build_search_queries)
  graph.add_node("search_public_web", search_public_web)
  graph.add_node("search_kopis_official", search_kopis_official)
  graph.add_node("infer_venue_from_search", infer_venue_from_search)
  graph.add_node("infer_event_candidates", infer_event_candidates)
  graph.add_node("extract_event_info", extract_event_info)
  graph.add_node("classify_sources", classify_sources)
  graph.add_node("summarize_information", summarize_information)
  graph.add_node("assign_confidence", assign_confidence)
  graph.add_node("format_response", format_response)

  graph.set_entry_point("analyze_input")
  for current_node, next_node in zip(NODE_SEQUENCE, NODE_SEQUENCE[1:]):
    graph.add_edge(current_node, next_node)
  graph.add_edge("format_response", END)

  return graph.compile()
