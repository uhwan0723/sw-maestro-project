from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def test_text_ingestion_stores_raw_document_chunks_and_cards(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    workspace_response = client.post(
        "/api/workspaces",
        json={"name": "SOMA 49", "description": "Sample workspace"},
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    ingestion_response = client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "meeting.md",
            "content": "가설: 사용자는 멘토링 전에 검증할 질문을 찾고 싶다.",
        },
    )

    assert ingestion_response.status_code == 201
    body = ingestion_response.json()
    assert body["document_id"] == 1
    assert body["chunk_count"] == 1
    assert body["card_count"] == 1
    assert body["skipped_chunk_count"] == 0
    assert body["new_card_ids"] == [1]
    assert body["needs_review_count"] == 0

    documents_response = client.get(f"/api/workspaces/{workspace_id}/documents")
    assert documents_response.status_code == 200
    assert documents_response.json()[0]["filename"] == "meeting.md"

    detail_response = client.get(f"/api/workspaces/{workspace_id}/documents/{body['document_id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["content"] == "가설: 사용자는 멘토링 전에 검증할 질문을 찾고 싶다."


def test_upload_rejects_unsupported_file_type(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/upload",
        files={"file": ("audio.mp3", b"not supported", "audio/mpeg")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_storage_preprocessing_extracts_cards_from_meeting_style_markdown(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "mentor-review.md",
            "source_type": "notion",
            "content": "\n".join(
                [
                    "# 5월 멘토링",
                    "",
                    "## 결정사항",
                    "",
                    "MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다. 근거: 2주 안에 Neo4j 운영은 어렵다.",
                    "",
                    "## 리스크",
                    "",
                    "- 관계가 많아지면 multi-hop 탐색 속도가 떨어질 수 있다.",
                ]
            ),
        },
    )

    assert response.status_code == 201
    assert response.json()["chunk_count"] == 2
    assert response.json()["card_count"] == 3
    assert response.json()["skipped_chunk_count"] == 0
    assert len(response.json()["new_card_ids"]) == 3
    assert response.json()["needs_review_count"] == 0

    cards = client.get(f"/api/workspaces/{workspace_id}/cards").json()
    assert [card["card_type"] for card in cards] == ["decision", "evidence", "risk"]
    assert cards[0]["summary"] == "MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다."
    assert cards[1]["summary"] == "2주 안에 Neo4j 운영은 어렵다."
    assert cards[2]["summary"] == "관계가 많아지면 multi-hop 탐색 속도가 떨어질 수 있다."
