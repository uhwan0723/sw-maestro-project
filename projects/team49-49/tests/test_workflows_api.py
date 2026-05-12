from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def test_workflows_api_returns_langgraph_registry(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get("/api/workflows")

    assert response.status_code == 200
    data = response.json()
    assert data["runtime"] == "LangGraph StateGraph"
    assert len(data["flows"]) == 5
    assert data["links"][0]["source"] == "source_intake"
    assert {flow["owner"] for flow in data["flows"]} == {"김지환", "윤영준", "이용준", "이진우", "조은성"}
    source_flow = next(flow for flow in data["flows"] if flow["id"] == "source_intake")
    assert source_flow["status"] == "implemented"
    assert source_flow["workflow_file"] == "app/workflows/source_intake.py"
    assert source_flow["nodes"] == [
        "validate_input",
        "select_connector",
        "fetch_external_content",
        "normalize_document",
        "finalize",
    ]
