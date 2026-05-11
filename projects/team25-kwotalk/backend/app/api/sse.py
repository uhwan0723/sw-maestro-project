"""LangGraph astream_events → SSE 변환.

이벤트 타입:
  meta       : 노드 진입/종료, 라우팅 정보
  token      : LLM 토큰 단위 스트림 (generate_node)
  state      : 노드 종료 시점의 부분 상태 스냅샷
  done       : 그래프 종료, 최종 상태 포함
  error      : 예외
"""
import json
from typing import AsyncIterator, Any


def _format(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_STREAMABLE_NODES = {"generate"}


async def stream_graph_events(graph, inputs: dict, config: dict | None = None) -> AsyncIterator[str]:
    config = config or {}
    try:
        async for ev in graph.astream_events(inputs, config=config, version="v2"):
            kind = ev.get("event")
            name = ev.get("name", "")
            data: dict[str, Any] = ev.get("data", {})

            if kind == "on_chain_start" and name in {
                "classify", "clarify", "retrieve", "guide",
                "settlement", "generate", "post_check", "fallback",
            }:
                yield _format("meta", {"phase": "start", "node": name})

            elif kind == "on_chat_model_stream" and name in _STREAMABLE_NODES:
                chunk = data.get("chunk")
                token = getattr(chunk, "content", None) if chunk else None
                if token:
                    yield _format("token", {"text": token})

            elif kind == "on_chain_end" and name in {
                "classify", "clarify", "retrieve", "guide",
                "settlement", "generate", "post_check", "fallback",
            }:
                output = data.get("output") or {}
                yield _format("state", {"node": name, "patch": _safe(output)})

        yield _format("done", {})
    except Exception as e:
        yield _format("error", {"message": str(e)})


def _safe(obj: Any) -> Any:
    """JSON 직렬화 안전 변환."""
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)
