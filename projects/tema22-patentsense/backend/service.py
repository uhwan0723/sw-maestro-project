from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from agent.graph import agent

PROGRESS_MESSAGES = {
    "extract_keywords": "키워드 추출",
    "search_patents": "특허 검색",
    "rank_by_similarity": "유사도 계산",
    "analyze_conflicts": "충돌 요소 분석",
    "derive_differentiators": "차별화 포인트 도출",
    "generate_report": "리포트 생성",
}


def _initial_state(idea_text: str) -> dict[str, Any]:
    return {
        "user_idea": idea_text,
        "processed_idea": "",
        "preprocess_detail": {},
        "keywords": [],
        "patents": [],
        "ranked_patents": [],
        "report": "",
        "conflict_points": [],
        "differentiators": [],
        "messages": [],
        "error": None,
    }


def _summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    ranked = state.get("ranked_patents", []) or []

    return {
        "report": state.get("report", ""),
        "keywords": state.get("keywords", []),
        "conflict_points": state.get("conflict_points", []),
        "differentiators": state.get("differentiators", []),
        "top_patents": [
            {
                "application_number": p.get("application_number", ""),
                "title": p.get("title", ""),
                "similarity_score": p.get("similarity_score", 0),
                "applicant": p.get("applicant", ""),
                "register_status": p.get("register_status", ""),
                "open_date": p.get("open_date", ""),
            }
            for p in ranked[:5]
        ],
    }


def _build_progress_payload(node_name: str, updates: dict[str, Any]) -> dict[str, Any]:
    if node_name == "extract_keywords":
        return {"keywords": updates.get("keywords", [])}
    if node_name == "search_patents":
        return {
            "count": len(updates.get("patents", []) or []),
            "error": updates.get("error"),
        }
    if node_name == "rank_by_similarity":
        ranked = updates.get("ranked_patents", []) or []
        return {
            "count": len(ranked),
            "top_score": ranked[0].get("similarity_score", 0) if ranked else 0,
        }
    if node_name == "analyze_conflicts":
        return {"count": len(updates.get("conflict_points", []) or [])}
    if node_name == "derive_differentiators":
        return {"count": len(updates.get("differentiators", []) or [])}
    if node_name == "generate_report":
        return {"report_length": len(updates.get("report", "") or "")}
    return {"updates": updates}


def analyze_idea(idea_text: str) -> dict[str, Any]:
    """Run the full agent and return the final structured result."""
    final_state = agent.invoke(_initial_state(idea_text))
    return _summarize_state(final_state)


def stream_analysis_events(idea_text: str) -> Iterator[dict[str, Any]]:
    """Yield structured progress events while the LangGraph agent runs."""
    yield {
        "event": "status",
        "step": "queued",
        "message": "분석을 시작했어.",
    }

    final_state = _initial_state(idea_text)

    try:
        for chunk in agent.stream(final_state):
            node_name = next(iter(chunk))
            updates = chunk[node_name]
            final_state.update(updates)

            payload = {
                "event": "progress",
                "step": node_name,
                "message": PROGRESS_MESSAGES.get(node_name, node_name),
                "data": _build_progress_payload(node_name, updates),
            }
            yield payload

        yield {
            "event": "done",
            "step": "complete",
            "message": "분석이 완료됐어.",
            "data": _summarize_state(final_state),
        }
    except Exception as exc:  # noqa: BLE001
        yield {
            "event": "error",
            "step": "failed",
            "message": str(exc),
        }


def to_sse(event: dict[str, Any]) -> str:
    name = event.get("event", "message")
    return f"event: {name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
