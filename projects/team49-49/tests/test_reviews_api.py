from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def test_review_api_collects_quality_targets_without_mutating_cards(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    ingestion = client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "raw-note.md",
            "content": "질문: GraphDB와 SQLite 대안 중 무엇을 선택해야 하는가?",
        },
    ).json()

    response = client.post(f"/api/workspaces/{workspace_id}/reviews/run")

    assert response.status_code == 200
    body = response.json()
    assert body["workspace_id"] == workspace_id
    assert body["target_count"] == 1
    needs_review_target = next(target for target in body["targets"] if target["reason"] == "needs_review status")
    assert needs_review_target["card_id"] == ingestion["new_card_ids"][0]
    assert needs_review_target["priority"] == "high"
    assert needs_review_target["reasons"] == ["needs_review status", "low confidence"]
    assert body["summary"]["needs_review"] == 1
    assert body["summary"]["low_confidence"] == 1
    assert client.get(f"/api/workspaces/{workspace_id}/cards").json()[0]["status"] == "needs_review"
