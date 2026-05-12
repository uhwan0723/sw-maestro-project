from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.services.source_connectors import SourceFetchResult


class FakeSourceConnector:
    def __init__(self, *, title: str, content: str, external_id: str = "external-auto-id"):
        self.title = title
        self.content = content
        self.external_id = external_id
        self.calls: list[tuple[str, str]] = []

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        self.calls.append((source_url, external_id))
        return SourceFetchResult(
            title=self.title,
            content=self.content,
            external_id=external_id or self.external_id,
            fetched_via="fake_e2e_connector",
        )


def _client(tmp_path, connector: FakeSourceConnector | None = None) -> tuple[TestClient, int, FakeSourceConnector | None]:
    repository = SQLiteRepository(tmp_path / "ich-e2e.sqlite3")
    app = create_app(repository=repository)
    app.state.settings.upstage_api_key = ""
    if connector:
        app.state.source_connector_registry = {"github": connector, "notion": connector, "web": connector}
    client = TestClient(app)
    workspace_id = client.post(
        "/api/workspaces",
        json={"name": "E2E Source Intake", "description": "source intake regression"},
    ).json()["id"]
    return client, workspace_id, connector


def test_e2e_auto_fetch_source_to_cards_graph_search_and_qa_history(tmp_path):
    connector = FakeSourceConnector(
        title="github-prd.md",
        content="\n".join(
            [
                "아이디어: GitHub PRD 링크만 넣어도 Source Intake가 원문을 가져와 카드로 저장한다.",
                "가설: 사용자는 PRD 링크를 복사하는 것만으로 팀 컨텍스트를 갱신하고 싶다.",
                "근거: 데모 체크리스트에서 Notion, GitHub, Linear 자동 연동이 필수로 언급됐다.",
                "결정: Source Intake는 서버 토큰으로만 외부 provider를 읽고 frontend에 token을 노출하지 않는다.",
            ]
        ),
        external_id="github:org/repo/prd.md",
    )
    client, workspace_id, connector = _client(tmp_path, connector)

    intake_response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "github",
            "source_url": "https://github.com/org/repo/blob/main/docs/prd.md",
            "external_id": "",
            "title": "",
            "content": "",
        },
    )

    assert intake_response.status_code == 201
    assert connector is not None
    assert connector.calls == [("https://github.com/org/repo/blob/main/docs/prd.md", "")]
    assert intake_response.json()["card_count"] == 4

    document = client.get(
        f"/api/workspaces/{workspace_id}/documents/{intake_response.json()['document_id']}"
    ).json()
    assert document["filename"] == "github-prd.md"
    assert document["source_type"] == "github"
    assert document["source_url"].endswith("/docs/prd.md")
    assert document["external_id"] == "github:org/repo/prd.md"

    cards = client.get(f"/api/workspaces/{workspace_id}/cards").json()
    assert {card["card_type"] for card in cards} >= {"idea", "hypothesis", "evidence", "decision"}
    assert any("frontend에 token을 노출하지 않는다" in card["summary"] for card in cards)

    graph = client.get(f"/api/workspaces/{workspace_id}/graph").json()
    assert any(node["id"] == f"doc:{document['id']}" for node in graph["nodes"])
    assert sum(1 for link in graph["links"] if link["type"] == "contains") == len(cards)

    search = client.get(
        f"/api/workspaces/{workspace_id}/search",
        params={"q": "GitHub PRD 자동 연동 token"},
    ).json()
    assert search["cards"]
    assert search["chunks"]
    assert search["cards"][0]["source_document_id"] == document["id"]

    llm_response = client.post(
        f"/api/workspaces/{workspace_id}/search/llm",
        json={"query": "GitHub PRD 링크는 어떻게 저장돼?"},
    )
    assert llm_response.status_code == 200
    answer = llm_response.json()
    assert answer["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."
    assert answer["evidence_cards"]
    assert answer["evidence_chunks"]

    qa_history = client.get(f"/api/workspaces/{workspace_id}/qa/history").json()
    assert qa_history[-1]["question"] == "GitHub PRD 링크는 어떻게 저장돼?"
    assert qa_history[-1]["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."


def test_e2e_pasted_content_takes_priority_over_connector_fetch(tmp_path):
    connector = FakeSourceConnector(
        title="should-not-be-used.md",
        content="아이디어: 이 내용은 저장되면 안 된다.",
    )
    client, workspace_id, connector = _client(tmp_path, connector)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "notion",
            "source_url": "https://notion.so/team/source-intake",
            "external_id": "manual-notion-page",
            "title": "manual-source.md",
            "content": "결정: pasted content가 있으면 provider fetch를 호출하지 않는다.",
        },
    )

    assert response.status_code == 201
    assert connector is not None
    assert connector.calls == []
    document = client.get(f"/api/workspaces/{workspace_id}/documents/{response.json()['document_id']}").json()
    assert document["filename"] == "manual-source.md"
    assert document["external_id"] == "manual-notion-page"
    assert "provider fetch를 호출하지 않는다" in document["content"]
    cards = client.get(f"/api/workspaces/{workspace_id}/cards", params={"card_type": "decision"}).json()
    assert len(cards) == 1


def test_e2e_upload_source_metadata_flows_to_graph_and_search(tmp_path):
    client, workspace_id, _ = _client(tmp_path)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents/upload",
        data={
            "source_type": "linear",
            "source_url": "https://linear.app/acme/issue/ICH-49/source-intake",
            "external_id": "ICH-49",
        },
        files={
            "file": (
                "linear-issue.md",
                "리스크: OAuth 토큰을 frontend로 노출하면 보안 사고가 발생할 수 있다.".encode("utf-8"),
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    document = client.get(f"/api/workspaces/{workspace_id}/documents/{response.json()['document_id']}").json()
    assert document["source_type"] == "linear"
    assert document["source_url"].endswith("/ICH-49/source-intake")
    assert document["external_id"] == "ICH-49"

    graph = client.get(f"/api/workspaces/{workspace_id}/graph").json()
    assert any(node["label"] == "linear-issue.md" for node in graph["nodes"])
    assert any(link["type"] == "contains" for link in graph["links"])

    search = client.get(
        f"/api/workspaces/{workspace_id}/search",
        params={"q": "OAuth 토큰 frontend 노출 보안"},
    ).json()
    assert search["cards"][0]["card_type"] == "risk"
    assert search["cards"][0]["source_document_id"] == document["id"]
