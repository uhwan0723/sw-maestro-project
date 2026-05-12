from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


ROOT = Path(__file__).resolve().parents[1]


def test_homepage_serves_react_studio_bundle(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert "/assets/index-" in response.text
    assert "<style>" not in response.text
    assert "<script " in response.text

    asset_paths = [
        part.split('"')[0]
        for part in response.text.split('href="')[1:]
        if part.startswith("/assets/")
    ] + [
        part.split('"')[0]
        for part in response.text.split('src="')[1:]
        if part.startswith("/assets/")
    ]
    assert asset_paths
    for asset_path in asset_paths:
        assert client.get(asset_path).status_code == 200


def test_frontend_source_matches_langgraph_studio_and_shadcn_contract():
    app_source = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    graph_source = (ROOT / "frontend" / "src" / "components" / "KnowledgeGraphPanel.tsx").read_text(encoding="utf-8")
    flow_source = (ROOT / "frontend" / "src" / "components" / "LangGraphFlowPanel.tsx").read_text(encoding="utf-8")
    obsidian_graph_source = (ROOT / "frontend" / "src" / "components" / "ObsidianGraphPanel.tsx").read_text(encoding="utf-8")
    css_source = (ROOT / "frontend" / "src" / "index.css").read_text(encoding="utf-8")

    assert "SidebarProvider" in app_source
    assert "SidebarInset" in app_source
    assert "CardHeader" in app_source
    assert "FieldGroup" in app_source
    assert "TabsList" in app_source
    assert "workflow-step-card" in app_source
    assert "size=\"sm\" className=\"workflow-step-card\"" in app_source
    assert "Graph Studio" in app_source
    assert "LangGraph Flow" in app_source
    assert "Multi-source ingestion" in app_source
    assert "Grounded LLM Search" in app_source
    assert "source-ingestion-form" in app_source
    assert "llm-search-form" in app_source
    assert "/api/workflows" in app_source

    assert "KnowledgeGraphPanel" in graph_source
    assert "onPointerDown" in graph_source
    assert "onPointerMove" in graph_source
    assert "markerEnd" in graph_source
    assert "GraphEdge" in graph_source
    assert "GraphNodeBox" in graph_source
    assert "buildSelectedNeighborhood" in graph_source
    assert "beginCanvasPan" in graph_source
    assert "closest(\".graph-node-box\")" in graph_source
    assert "graphPoint" in graph_source
    assert "zoomGraphStudio" in graph_source
    assert 'addEventListener("wheel"' in graph_source
    assert "passive: false" in graph_source
    assert "graph-studio-pan-zoom-layer" in graph_source
    assert "graph-studio-zoom-in" in graph_source
    assert "graph-studio-zoom-out" in graph_source
    assert "graph-studio-reset-view" in graph_source
    assert "graph-studio-legend" in graph_source
    assert "graph-reset-layout" in graph_source
    assert "graph-node-accent" in graph_source
    assert "is-dimmed" in graph_source

    assert "LangGraphFlowPanel" in flow_source
    assert "FlowRailNode" in flow_source
    assert "implemented" in flow_source
    assert "extension" in flow_source
    assert "input_contract" in flow_source
    assert "output_contract" in flow_source

    assert "ObsidianGraphPanel" in obsidian_graph_source
    assert "obsidian-graph-canvas" in obsidian_graph_source
    assert "obsidian-graph-stage" in obsidian_graph_source
    assert "obsidian-graph-search" in obsidian_graph_source
    assert "InputGroupInput" in obsidian_graph_source
    assert "InputGroupAddon" in obsidian_graph_source
    assert "obsidian-local-depth" in obsidian_graph_source
    assert "obsidian-link-distance" in obsidian_graph_source
    assert "obsidian-node-size" in obsidian_graph_source
    assert "onWheel" in obsidian_graph_source
    assert "requestAnimationFrame" in obsidian_graph_source
    assert "relaxObsidianNodes" in obsidian_graph_source
    assert "resetView" in obsidian_graph_source
    assert "focusSelection" in obsidian_graph_source
    assert "visibleNodeIds" in obsidian_graph_source
    assert "selectLabeledNodes" in obsidian_graph_source
    assert "clipObsidianLabel" in obsidian_graph_source
    assert "obsidian-link-label" in obsidian_graph_source
    assert "obsidian-empty-state" in obsidian_graph_source

    assert "@theme inline" in css_source
    assert "--color-sidebar" in css_source
    assert ".studio-graph-canvas" in css_source
    assert ".studio-graph-canvas.is-panning" in css_source
    assert ".graph-studio-legend" in css_source
    assert ".graph-node-accent" in css_source
    assert ".obsidian-graph-canvas" in css_source
    assert ".obsidian-graph-stage" in css_source
    assert ".obsidian-node" in css_source
    assert ".obsidian-link-label" in css_source
    assert ".obsidian-empty-state" in css_source
    assert "radial-gradient" not in css_source
    assert ".workflow-node" in css_source
    assert ".workflow-step-card" in css_source
    assert ".flow-rail" in css_source
    assert ".flow-card" in css_source


def test_frontend_supports_external_sources_and_llm_search_contract():
    app_source = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    samples_source = (ROOT / "frontend" / "src" / "lib" / "samples.ts").read_text(encoding="utf-8")

    assert "/documents/source" in app_source
    assert "/documents/upload" in app_source
    assert "/search/llm" in app_source
    assert "/search?q=" in app_source
    assert "notion" in samples_source
    assert "github" in samples_source
    assert "slack" in samples_source
    assert "linear" in samples_source
    assert "mcp" in samples_source
    assert "web" in samples_source
    assert "pdf" in samples_source


def test_favicon_request_serves_site_icon(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert b"<svg" in response.content


def test_homepage_avoids_forbidden_user_facing_label(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get("/")

    forbidden_english = "de" + "mo"
    forbidden_korean = "데" + "모"
    assert forbidden_english not in response.text.lower()
    assert forbidden_korean not in response.text
