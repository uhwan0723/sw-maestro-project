from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.services.qa import GroundedQAService, REMOTE_LANGGRAPH_FAILED_MESSAGE


INSUFFICIENT_MESSAGE = "현재까지 저장된 팀 컨텍스트에서는 관련된 논의나 근거를 찾을 수 없습니다."


def test_qa_reports_missing_upstage_api_key_and_persists_history(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    app.state.settings.upstage_api_key = ""
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]
    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "architecture.md",
            "content": "결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.\n\n근거: 2주 MVP에서 Neo4j는 쿼리 설계와 시각화 구현 리스크가 크다.",
        },
    )

    response = client.post(
        f"/api/workspaces/{workspace_id}/qa",
        json={"question": "왜 GraphDB를 제외했어?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."
    assert body["confidence"] == "low"
    assert body["evidence_cards"][0]["card_id"] >= 1
    assert body["evidence_cards"][0]["source_document"] == "architecture.md"
    assert body["evidence_chunks"][0]["source_document"] == "architecture.md"
    assert isinstance(body["missing_evidence"], list)

    history_response = client.get(f"/api/workspaces/{workspace_id}/qa/history")
    assert history_response.status_code == 200
    assert history_response.json()[0]["question"] == "왜 GraphDB를 제외했어?"


def test_qa_returns_insufficient_context_when_no_evidence_exists(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/qa",
        json={"question": "가격 정책은 어떻게 결정했어?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == INSUFFICIENT_MESSAGE
    assert body["confidence"] == "low"
    assert body["evidence_cards"] == []
    assert body["evidence_chunks"] == []
    assert body["missing_evidence"] == ["질문과 관련된 저장 컨텍스트가 부족합니다."]


class FakeRemoteLangGraphClient:
    def __init__(self):
        self.calls = []

    def is_configured(self, assistant_id: str | None = None) -> bool:
        return bool(assistant_id)

    def run(self, assistant_id: str, payload: dict) -> dict:
        self.calls.append({"assistant_id": assistant_id, "payload": payload})
        return {
            "generate_answer": {
                "result": {
                    "answer": "LangGraph SDK가 생성한 원격 graph 답변",
                    "confidence": "high",
                    "missing_evidence": [],
                }
            }
        }


def test_grounded_qa_prefers_remote_langgraph_when_configured(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="architecture.md",
        document_type="md",
        content="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )
    chunk = repository.create_chunks(
        document_id=document["id"],
        workspace_id=workspace["id"],
        contents=["결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다."],
    )[0]
    repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunk["id"],
        card_type="decision",
        title="SQLite relation 사용",
        summary="MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        evidence_quote="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        keywords=["GraphDB", "SQLite", "relation"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )
    remote = FakeRemoteLangGraphClient()

    answer = GroundedQAService(
        repository,
        remote_langgraph_client=remote,
        remote_qa_assistant_id="qa_assistant",
    ).answer(
        workspace_id=workspace["id"],
        question="왜 GraphDB를 제외했어?",
    )

    assert answer["answer"] == "LangGraph SDK가 생성한 원격 graph 답변"
    assert answer["confidence"] == "high"
    assert remote.calls[0]["assistant_id"] == "qa_assistant"
    assert remote.calls[0]["payload"]["question"] == "왜 GraphDB를 제외했어?"
    assert remote.calls[0]["payload"]["cards"][0]["title"] == "SQLite relation 사용"


def test_remote_qa_payload_includes_one_hop_relations_and_neighbor_cards(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="architecture.md",
        document_type="md",
        content="결정: GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )
    chunks = repository.create_chunks(
        document_id=document["id"],
        workspace_id=workspace["id"],
        contents=[
            "결정: GraphDB 대신 SQLite relation 테이블을 사용한다.",
            "근거: 2주 안에 Neo4j 운영은 어렵다.",
        ],
    )
    decision = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[0]["id"],
        card_type="decision",
        title="SQLite relation 사용",
        summary="GraphDB 대신 SQLite relation 테이블을 사용한다.",
        evidence_quote="결정: GraphDB 대신 SQLite relation 테이블을 사용한다.",
        keywords=["GraphDB", "SQLite", "relation"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )
    evidence = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[1]["id"],
        card_type="evidence",
        title="Neo4j 운영 리스크",
        summary="2주 안에 Neo4j 운영은 어렵다.",
        evidence_quote="근거: 2주 안에 Neo4j 운영은 어렵다.",
        keywords=["Neo4j", "운영"],
        tags=["validated"],
        status="validated",
        confidence="high",
    )
    repository.create_relation(workspace["id"], decision["id"], evidence["id"], "supports", "결정을 뒷받침하는 근거", "high")
    remote = FakeRemoteLangGraphClient()

    GroundedQAService(
        repository,
        remote_langgraph_client=remote,
        remote_qa_assistant_id="qa_assistant",
    ).answer(workspace["id"], "왜 GraphDB를 제외했어?")

    payload = remote.calls[0]["payload"]
    assert payload["schema_version"] == "qa_context_bundle.v1"
    assert payload["relations"][0]["relation_type"] == "supports"
    assert payload["neighbor_cards"][0]["id"] == evidence["id"]


def test_qa_response_evidence_and_history_include_neighbor_cards_used_for_context(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(workspace["id"], "architecture.md", "md", "content")
    chunks = repository.create_chunks(
        document_id=document["id"],
        workspace_id=workspace["id"],
        contents=["결정: GraphDB 대신 SQLite를 사용한다.", "근거: Neo4j 운영 시간이 부족하다."],
    )
    decision = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[0]["id"],
        card_type="decision",
        title="SQLite 사용",
        summary="GraphDB 대신 SQLite를 사용한다.",
        evidence_quote="결정: GraphDB 대신 SQLite를 사용한다.",
        keywords=["GraphDB", "SQLite"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )
    evidence = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[1]["id"],
        card_type="evidence",
        title="Neo4j 운영 시간 부족",
        summary="Neo4j 운영 시간이 부족하다.",
        evidence_quote="근거: Neo4j 운영 시간이 부족하다.",
        keywords=["Neo4j"],
        tags=["validated"],
        status="validated",
        confidence="high",
    )
    repository.create_relation(workspace["id"], decision["id"], evidence["id"], "supports", "결정 근거", "high")

    answer = GroundedQAService(repository).answer_from_search(
        workspace_id=workspace["id"],
        question="왜 GraphDB를 제외했어?",
        search={"cards": [decision], "chunks": []},
    )

    assert [card["card_id"] for card in answer["evidence_cards"]] == [decision["id"], evidence["id"]]
    assert repository.list_chat_history(workspace["id"])[0]["referenced_card_ids"] == [decision["id"], evidence["id"]]


class FailingRemoteLangGraphClient:
    def is_configured(self, assistant_id: str | None = None) -> bool:
        return bool(assistant_id)

    def run(self, assistant_id: str, payload: dict) -> dict:
        raise RuntimeError("remote unavailable")


def test_grounded_qa_reports_remote_failure_without_local_answer(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="architecture.md",
        document_type="md",
        content="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )
    chunk = repository.create_chunks(
        document_id=document["id"],
        workspace_id=workspace["id"],
        contents=["결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다."],
    )[0]
    repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunk["id"],
        card_type="decision",
        title="SQLite relation 사용",
        summary="MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        evidence_quote="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        keywords=["GraphDB", "SQLite", "relation"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )

    answer = GroundedQAService(
        repository,
        remote_langgraph_client=FailingRemoteLangGraphClient(),
        remote_qa_assistant_id="qa_assistant",
    ).answer(
        workspace_id=workspace["id"],
        question="왜 GraphDB를 제외했어?",
    )

    assert answer["answer"] == REMOTE_LANGGRAPH_FAILED_MESSAGE
    assert answer["confidence"] == "low"
    assert answer["evidence_cards"][0]["title"] == "SQLite relation 사용"
    assert answer["missing_evidence"] == ["LangGraph Q&A assistant가 유효한 답변을 반환하지 않았습니다."]


def test_qa_api_calls_upstage_when_api_key_is_set(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    app.state.settings.upstage_api_key = "test-key"
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]
    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "architecture.md",
            "content": "결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        },
    )

    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": '{"answer": "통합 그래프가 생성한 로컬 답변", "cited_card_ids": [1], "cited_chunk_ids": []}'}}]
    }

    with patch("app.services.qa_engine.httpx.post", return_value=fake_resp):
        response = client.post(f"/api/workspaces/{workspace_id}/qa", json={"question": "왜 GraphDB를 제외했어?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "통합 그래프가 생성한 로컬 답변"
    assert response.json()["confidence"] == "medium"
