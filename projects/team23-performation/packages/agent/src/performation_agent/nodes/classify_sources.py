from __future__ import annotations

from performation_agent.state import ClassifiedSource, GuideState
from performation_agent.tools.source_classifier import classify_search_result
from performation_domain import Source


def classify_sources(state: GuideState) -> GuideState:
  classified_sources: list[ClassifiedSource] = []
  venue = state.get("venue")

  if venue:
    classified_sources.extend(
      {"source": source, "reason": "로컬 공연장 fallback 데이터에 포함된 공식 또는 안정 정보입니다."}
      for source in venue.sources
    )

  for result in state.get("search_results", []):
    confidence_label, reason = classify_search_result(result)
    classified_sources.append(
      {
        "source": Source(
          title=result["title"],
          url=result["url"],
          source_type=confidence_label,
          used_for=[result["query"]],
        ),
        "reason": reason,
      }
    )

  return {
    "classified_sources": classified_sources,
    "sources": [item["source"] for item in classified_sources],
  }
