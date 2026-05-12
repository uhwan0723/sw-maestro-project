from typing import Any

import pytest
from fastapi.testclient import TestClient
from langgraph.graph.state import CompiledStateGraph

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.workflows.quality_review import QualityReviewWorkflow


def _make_repo(tmp_path):
    repo = SQLiteRepository(tmp_path / "test.sqlite3")
    repo.initialize()
    return repo


def _seed(repo: SQLiteRepository) -> tuple[dict, dict, dict]:
    workspace = repo.create_workspace("Test Workspace")
    doc = repo.create_raw_document(
        workspace_id=workspace["id"],
        filename="test.md",
        document_type="md",
        content="테스트 내용",
    )
    chunks = repo.create_chunks(doc["id"], workspace["id"], ["테스트 내용"])
    return workspace, doc, chunks[0]


def _make_card(repo: SQLiteRepository, workspace_id: int, doc_id: int, chunk_id: int, **kwargs: Any) -> dict:
    defaults: dict[str, Any] = {
        "card_type": "idea",
        "title": "테스트 카드",
        "summary": "테스트 요약입니다",
        "evidence_quote": "충분히 긴 근거 인용 텍스트입니다 30자 이상",
        "keywords": [],
        "tags": [],
        "status": "proposed",
        "confidence": "medium",
    }
    defaults.update(kwargs)
    return repo.create_knowledge_card(
        workspace_id=workspace_id,
        source_document_id=doc_id,
        source_chunk_id=chunk_id,
        **defaults,
    )


class FakeLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> str | None:
        return '{"issue": "근거 없음", "suggestion": "evidence 카드 추가 필요"}'


# --- Workflow 단위 테스트 ---

def test_workflow_is_compiled_langgraph(tmp_path):
    repo = _make_repo(tmp_path)
    workflow = QualityReviewWorkflow(repo)
    assert isinstance(workflow.graph, CompiledStateGraph)


def test_empty_workspace_returns_zero(tmp_path):
    repo = _make_repo(tmp_path)
    workspace = repo.create_workspace("Empty")
    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    assert result["total_cards"] == 0
    assert result["reviewed_count"] == 0
    assert result["review_targets"] == []


def test_collect_candidates_includes_low_confidence(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"],
               title="낮은 신뢰도", confidence="low")

    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    titles = [t["title"] for t in result["review_targets"]]
    assert "낮은 신뢰도" in titles


def test_collect_candidates_includes_needs_review(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"],
               title="검토 필요 카드", status="needs_review")

    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    titles = [t["title"] for t in result["review_targets"]]
    assert "검토 필요 카드" in titles


def test_collect_candidates_includes_isolated_cards(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"],
               title="고립된 카드", confidence="high", status="validated")

    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    titles = [t["title"] for t in result["review_targets"]]
    assert "고립된 카드" in titles


def test_analyze_cards_without_llm_uses_rules(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"],
               title="가설 카드", card_type="hypothesis", confidence="low",
               evidence_quote="짧음")

    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    assert result["reviewed_count"] >= 1
    target = result["review_targets"][0]
    assert target["issue"]
    assert target["suggestion"]


def test_analyze_cards_with_mock_llm(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"], confidence="low")

    workflow = QualityReviewWorkflow(repo, llm_client=FakeLLMClient())
    result = workflow.run(workspace["id"])

    assert result["reviewed_count"] >= 1
    target = result["review_targets"][0]
    assert target["issue"] == "근거 없음"
    assert target["suggestion"] == "evidence 카드 추가 필요"


def test_full_workflow_result_structure(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"], confidence="low")

    workflow = QualityReviewWorkflow(repo)
    result = workflow.run(workspace["id"])

    assert "total_cards" in result
    assert "reviewed_count" in result
    assert "review_targets" in result
    assert "quality_summary" in result
    assert isinstance(result["review_targets"], list)
    assert isinstance(result["quality_summary"], str)


def test_update_statuses_marks_cards_needs_review(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    card = _make_card(repo, workspace["id"], doc["id"], chunk["id"],
                      status="proposed", confidence="low")

    workflow = QualityReviewWorkflow(repo)
    workflow.run(workspace["id"])

    updated = repo.get_card(card["id"])
    assert updated["status"] == "needs_review"


def test_update_statuses_does_not_override_decided(tmp_path):
    repo = _make_repo(tmp_path)
    workspace, doc, chunk = _seed(repo)
    card = _make_card(repo, workspace["id"], doc["id"], chunk["id"],
                      status="decided", confidence="low")

    workflow = QualityReviewWorkflow(repo)
    workflow.run(workspace["id"])

    updated = repo.get_card(card["id"])
    assert updated["status"] == "decided"


# --- API 테스트 ---

def test_run_review_endpoint_returns_200(tmp_path):
    repo = _make_repo(tmp_path)
    app = create_app(repository=repo)
    app.state.settings.llm_provider = "none"
    app.state.settings.upstage_api_key = ""
    client = TestClient(app)
    workspace = repo.create_workspace("SOMA 49")

    response = client.post(f"/api/workspaces/{workspace['id']}/reviews/run")

    assert response.status_code == 200
    data = response.json()
    assert "total_cards" in data
    assert "reviewed_count" in data
    assert "review_targets" in data
    assert "quality_summary" in data


def test_run_review_with_cards_returns_targets(tmp_path):
    repo = _make_repo(tmp_path)
    app = create_app(repository=repo)
    app.state.settings.llm_provider = "none"
    app.state.settings.upstage_api_key = ""
    client = TestClient(app)
    workspace, doc, chunk = _seed(repo)
    _make_card(repo, workspace["id"], doc["id"], chunk["id"], confidence="low")

    response = client.post(f"/api/workspaces/{workspace['id']}/reviews/run")

    assert response.status_code == 200
    assert response.json()["reviewed_count"] >= 1


def test_run_review_with_empty_workspace_returns_zero(tmp_path):
    repo = _make_repo(tmp_path)
    app = create_app(repository=repo)
    app.state.settings.llm_provider = "none"
    app.state.settings.upstage_api_key = ""
    client = TestClient(app)
    workspace = repo.create_workspace("Empty Workspace")

    response = client.post(f"/api/workspaces/{workspace['id']}/reviews/run")

    assert response.status_code == 200
    assert response.json()["reviewed_count"] == 0
