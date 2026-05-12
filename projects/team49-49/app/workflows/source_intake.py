from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.services.source_connectors import SourceConnector, SourceFetchResult, build_source_connector_registry
from app.services.sources import SUPPORTED_SOURCE_TYPES, filename_from_source, normalize_source_type


class SourceIntakeInput(BaseModel):
    workspace_id: int = Field(..., ge=1, description="Workspace id that will own the normalized document.")
    source_type: str = Field(
        ...,
        description="Source provider or local type, such as notion, github, slack, linear, mcp, web, manual, upload, or csv.",
    )
    source_url: str = Field("", description="Provider URL or public web URL. Leave empty when pasting content.")
    external_id: str = Field("", description="Provider-native id, issue key, Slack ts URI, or MCP resource URI.")
    title: str = Field("", description="Optional filename/title override.")
    content: str = Field("", description="Optional pasted/exported content. When set, external fetch is skipped.")


class SourceIntakeState(TypedDict, total=False):
    workspace_id: int
    source_type: str
    source_url: str
    external_id: str
    title: str
    content: str
    connector_name: str
    fetch_result: SourceFetchResult
    normalized: dict[str, Any]
    result: dict[str, Any]


class SourceIntakeWorkflow:
    def __init__(
        self,
        settings: Any | None = None,
        connectors: dict[str, SourceConnector] | None = None,
    ):
        self.connectors = connectors if connectors is not None else build_source_connector_registry(settings or object())
        self.graph = self._build_graph()

    def normalize(
        self,
        workspace_id: int,
        source_type: str,
        source_url: str = "",
        external_id: str = "",
        title: str = "",
        content: str = "",
    ) -> dict[str, Any]:
        state = self.graph.invoke(
            {
                "workspace_id": workspace_id,
                "source_type": source_type,
                "source_url": source_url,
                "external_id": external_id,
                "title": title,
                "content": content,
            }
        )
        return state["result"]

    def _build_graph(self):
        graph = StateGraph(SourceIntakeState, input_schema=SourceIntakeInput)
        graph.add_node("validate_input", self._validate_input)
        graph.add_node("select_connector", self._select_connector)
        graph.add_node("fetch_external_content", self._fetch_external_content)
        graph.add_node("normalize_document", self._normalize_document)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "validate_input")
        graph.add_edge("validate_input", "select_connector")
        graph.add_edge("select_connector", "fetch_external_content")
        graph.add_edge("fetch_external_content", "normalize_document")
        graph.add_edge("normalize_document", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _validate_input(self, state: SourceIntakeState) -> SourceIntakeState:
        source_type = normalize_source_type(state.get("source_type"), default="manual")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise ValueError(f"Unsupported source type: {source_type}")
        content = (state.get("content") or "").strip()
        source_url = (state.get("source_url") or "").strip()
        external_id = (state.get("external_id") or "").strip()
        if not content and not source_url and not external_id:
            raise ValueError("Either content, source_url, or external_id is required.")
        return {
            "source_type": source_type,
            "content": content,
            "source_url": source_url,
            "external_id": external_id,
            "title": (state.get("title") or "").strip(),
        }

    def _select_connector(self, state: SourceIntakeState) -> SourceIntakeState:
        if state.get("content"):
            return {"connector_name": ""}
        connector = self.connectors.get(state["source_type"])
        if connector is None:
            raise ValueError(f"Source type '{state['source_type']}' does not support automatic fetch. Paste content or upload a file.")
        return {"connector_name": state["source_type"]}

    def _fetch_external_content(self, state: SourceIntakeState) -> SourceIntakeState:
        if state.get("content"):
            return {
                "fetch_result": SourceFetchResult(
                    title=state.get("title", ""),
                    content=state["content"],
                    external_id=state.get("external_id", ""),
                    source_url=state.get("source_url", ""),
                    fetched_via="pasted",
                )
            }
        connector = self.connectors.get(state.get("connector_name", ""))
        if connector is None:
            raise ValueError("Automatic source fetch is not configured for this source type.")
        return {"fetch_result": connector.fetch(state.get("source_url", ""), state.get("external_id", ""))}

    def _normalize_document(self, state: SourceIntakeState) -> SourceIntakeState:
        fetch_result = state["fetch_result"]
        return {
            "normalized": self._normalize_fetch_result(
                fetch_result,
                workspace_id=state["workspace_id"],
                source_type=state["source_type"],
                source_url=state.get("source_url", ""),
                external_id=state.get("external_id", ""),
                title=state.get("title", ""),
            )
        }

    def _normalize_fetch_result(
        self,
        fetch_result: SourceFetchResult,
        workspace_id: int,
        source_type: str,
        source_url: str = "",
        external_id: str = "",
        title: str = "",
    ) -> dict[str, Any]:
        content = fetch_result.content.strip()
        if not content:
            raise ValueError("Source content is empty after normalization.")
        result_source_url = fetch_result.source_url or source_url
        result_external_id = fetch_result.external_id or external_id
        filename = filename_from_source(title or fetch_result.title, source_type, result_source_url)
        document_type = Path(filename).suffix.lower().lstrip(".") or "text"
        return {
            "workspace_id": workspace_id,
            "filename": filename,
            "content": content,
            "source_type": source_type,
            "source_url": result_source_url,
            "external_id": result_external_id,
            "document_type": document_type,
            "fetched_via": fetch_result.fetched_via,
            "child_documents": [
                self._normalize_fetch_result(
                    child,
                    workspace_id=workspace_id,
                    source_type=source_type,
                    source_url=child.source_url or result_source_url,
                    external_id=child.external_id,
                )
                for child in fetch_result.child_documents
            ],
        }

    def _finalize(self, state: SourceIntakeState) -> SourceIntakeState:
        return {"result": state["normalized"]}
