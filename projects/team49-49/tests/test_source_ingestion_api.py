from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.services.source_connectors import SourceFetchResult


def test_source_ingestion_preserves_external_metadata_and_llm_search(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    app.state.settings.upstage_api_key = ""
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    ingestion_response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "notion",
            "source_url": "https://notion.so/workspace/architecture",
            "external_id": "notion-page-architecture",
            "title": "architecture-note.md",
            "content": "결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.\n\n근거: 2주 안에 Neo4j를 운영하기 어렵다.",
        },
    )

    assert ingestion_response.status_code == 201
    document_id = ingestion_response.json()["document_id"]

    document_response = client.get(f"/api/workspaces/{workspace_id}/documents/{document_id}")
    document = document_response.json()
    assert document_response.status_code == 200
    assert document["source_type"] == "notion"
    assert document["source_url"] == "https://notion.so/workspace/architecture"
    assert document["external_id"] == "notion-page-architecture"

    llm_search_response = client.post(
        f"/api/workspaces/{workspace_id}/search/llm",
        json={"query": "왜 GraphDB를 제외했어?"},
    )

    assert llm_search_response.status_code == 200
    body = llm_search_response.json()
    assert body["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."
    assert body["query"] == "왜 GraphDB를 제외했어?"
    assert body["evidence_cards"][0]["source_document"] == "architecture-note.md"


def test_upload_accepts_source_metadata_form_fields(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/upload",
        data={
            "source_type": "github",
            "source_url": "https://github.com/org/repo/blob/main/prd.md",
            "external_id": "org/repo:prd.md",
        },
        files={"file": ("prd.md", "아이디어: GitHub PRD를 카드로 저장한다.".encode("utf-8"), "text/markdown")},
    )

    assert response.status_code == 201
    document_id = response.json()["document_id"]
    document = client.get(f"/api/workspaces/{workspace_id}/documents/{document_id}").json()
    assert document["source_type"] == "github"
    assert document["source_url"].endswith("/prd.md")
    assert document["external_id"] == "org/repo:prd.md"


class FakeSourceConnector:
    def __init__(self):
        self.calls = []

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        self.calls.append((source_url, external_id))
        return SourceFetchResult(
            title="auto-notion.md",
            content="결정: URL만 넣어도 Notion 문서를 자동으로 가져온다.",
            external_id=external_id or "notion-auto-id",
            fetched_via="notion_api",
        )


def test_source_ingestion_auto_fetches_when_content_is_empty(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    fake_connector = FakeSourceConnector()
    app.state.source_connector_registry = {"notion": fake_connector}
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "notion",
            "source_url": "https://notion.so/team/auto-notion",
            "external_id": "",
            "title": "",
            "content": "",
        },
    )

    assert response.status_code == 201
    document = client.get(f"/api/workspaces/{workspace_id}/documents/{response.json()['document_id']}").json()
    assert fake_connector.calls == [("https://notion.so/team/auto-notion", "")]
    assert document["filename"] == "auto-notion.md"
    assert document["source_type"] == "notion"
    assert document["source_url"] == "https://notion.so/team/auto-notion"
    assert document["external_id"] == "notion-auto-id"
    assert document["content"] == "결정: URL만 넣어도 Notion 문서를 자동으로 가져온다."


class FakeNotionTreeConnector:
    def __init__(self):
        self.calls = []

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        self.calls.append((source_url, external_id))
        return SourceFetchResult(
            title="parent-spec.md",
            content="결정: parent page는 child page와 별도 문서로 저장한다.",
            external_id="parent-page",
            source_url=source_url,
            fetched_via="notion_api",
            child_documents=[
                SourceFetchResult(
                    title="child-spec.md",
                    content="가설: child page도 카드로 추출되어 parent와 hop으로 연결된다.",
                    external_id="child-page",
                    source_url="https://notion.so/child-page",
                    fetched_via="notion_api",
                )
            ],
        )


def test_source_ingestion_imports_notion_child_pages_as_documents_and_graph_hops(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    fake_connector = FakeNotionTreeConnector()
    app.state.source_connector_registry = {"notion": fake_connector}
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "notion",
            "source_url": "https://notion.so/parent-page",
            "external_id": "",
            "title": "",
            "content": "",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["card_count"] == 2
    assert body["child_document_ids"]
    assert body["document_link_count"] == 1

    documents = client.get(f"/api/workspaces/{workspace_id}/documents").json()
    assert [document["filename"] for document in documents] == ["parent-spec.md", "child-spec.md"]
    assert documents[0]["external_id"] == "parent-page"
    assert documents[1]["external_id"] == "child-page"
    assert documents[1]["source_url"] == "https://notion.so/child-page"

    cards = client.get(f"/api/workspaces/{workspace_id}/cards").json()
    assert {card["source_document_id"] for card in cards} == {documents[0]["id"], documents[1]["id"]}

    graph = client.get(f"/api/workspaces/{workspace_id}/graph").json()
    assert any(
        link["source"] == f"doc:{documents[0]['id']}"
        and link["target"] == f"doc:{documents[1]['id']}"
        and link["type"] == "child_page"
        for link in graph["links"]
    )


def test_source_ingestion_prefers_pasted_content_over_auto_fetch(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    fake_connector = FakeSourceConnector()
    app.state.source_connector_registry = {"notion": fake_connector}
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "notion",
            "source_url": "https://notion.so/team/auto-notion",
            "external_id": "manual-id",
            "title": "manual.md",
            "content": "결정: 붙여넣은 내용이 자동 fetch보다 우선한다.",
        },
    )

    assert response.status_code == 201
    document = client.get(f"/api/workspaces/{workspace_id}/documents/{response.json()['document_id']}").json()
    assert fake_connector.calls == []
    assert document["filename"] == "manual.md"
    assert document["external_id"] == "manual-id"
    assert document["content"] == "결정: 붙여넣은 내용이 자동 fetch보다 우선한다."


def test_source_ingestion_rejects_unsupported_source_type(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "dropbox",
            "source_url": "https://dropbox.example/file",
            "external_id": "",
            "title": "",
            "content": "",
        },
    )

    assert response.status_code == 400
    assert "Unsupported source type" in response.text


def test_source_ingestion_reports_missing_provider_token_for_url_only_requests(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "github",
            "source_url": "https://github.com/org/repo/blob/main/docs/prd.md",
            "external_id": "",
            "title": "",
            "content": "",
        },
    )

    assert response.status_code == 400
    assert "ICH_GITHUB_TOKEN" in response.text
