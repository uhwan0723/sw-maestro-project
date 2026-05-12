from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.services.embeddings import DeterministicEmbedder, cosine_similarity
from app.services.relations import RelationLinkingService


def test_deterministic_similarity_scores_related_text_higher():
    embedder = DeterministicEmbedder()

    query = embedder.embed("멘토링 준비 질문")
    related = embedder.embed("멘토링 전에 준비할 질문을 정리한다")
    unrelated = embedder.embed("결제 모델과 가격 정책을 검토한다")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


class StaticRelationDetector:
    def __init__(self, relation_type: str):
        self.relation_type = relation_type

    def detect(self, new_card, existing_cards):
        return [
            {
                "source_card_id": new_card["id"],
                "target_card_id": existing["id"],
                "relation_type": self.relation_type,
                "reason": f"{new_card['id']} {self.relation_type} {existing['id']}",
                "confidence": "high",
            }
            for existing in existing_cards
        ]


def test_relation_linking_keeps_directional_relation_duplicates_distinct(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(workspace["id"], "relations.md", "md", "content")
    chunks = repository.create_chunks(document["id"], workspace["id"], ["a", "b"])
    first = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[0]["id"],
        card_type="decision",
        title="A",
        summary="A",
        evidence_quote="A",
        keywords=[],
        tags=[],
        status="decided",
        confidence="high",
    )
    second = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[1]["id"],
        card_type="evidence",
        title="B",
        summary="B",
        evidence_quote="B",
        keywords=[],
        tags=[],
        status="validated",
        confidence="high",
    )
    linker = RelationLinkingService(repository, StaticRelationDetector("supports"))

    linker.link_new_card(workspace["id"], first, [second])
    linker.link_new_card(workspace["id"], second, [first])

    relations = repository.list_relations(workspace["id"])
    assert [(relation["source_card_id"], relation["target_card_id"]) for relation in relations] == [
        (first["id"], second["id"]),
        (second["id"], first["id"]),
    ]


def test_cards_search_and_relation_api(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "meeting-1.md",
            "content": "아이디어: 멘토링 준비 질문을 자동 정리한다.\n\n가설: 사용자는 멘토링 준비 시간을 줄이고 싶다.",
        },
    )
    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "meeting-2.md",
            "content": "아이디어: 멘토링 준비 질문을 자동 정리한다.",
        },
    )

    cards_response = client.get(f"/api/workspaces/{workspace_id}/cards", params={"card_type": "idea"})
    assert cards_response.status_code == 200
    idea_cards = cards_response.json()
    assert len(idea_cards) == 2

    detail_response = client.get(f"/api/workspaces/{workspace_id}/cards/{idea_cards[0]['id']}")
    detail = detail_response.json()
    assert detail_response.status_code == 200
    assert detail["source_document"]["filename"] == "meeting-1.md"
    assert detail["source_chunk"]["content"].startswith("아이디어:")

    relations_response = client.get(f"/api/workspaces/{workspace_id}/cards/{idea_cards[1]['id']}/relations")
    relations = relations_response.json()
    assert relations_response.status_code == 200
    assert any(relation["relation_type"] == "duplicates" for relation in relations)

    search_response = client.get(f"/api/workspaces/{workspace_id}/search", params={"q": "멘토링 준비"})
    search = search_response.json()
    assert search_response.status_code == 200
    assert search["cards"][0]["title"] == "멘토링 준비 질문을 자동 정리한다."
    assert search["chunks"][0]["content"].startswith("아이디어:")


def test_graph_api_links_documents_through_related_cards(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "mentor-meeting.md",
            "content": "아이디어: 멘토링 준비 질문을 자동 정리한다.",
        },
    )
    client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "ai-chat.md",
            "content": "아이디어: 멘토링 준비 질문을 자동 정리한다.",
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/graph")

    assert response.status_code == 200
    graph = response.json()
    node_ids = {node["id"] for node in graph["nodes"]}
    link_types = {link["type"] for link in graph["links"]}
    assert "doc:1" in node_ids
    assert "doc:2" in node_ids
    assert "card:1" in node_ids
    assert "card:2" in node_ids
    assert "contains" in link_types
    assert "duplicates" in link_types
    assert "document_link" in link_types


def test_card_paths_api_returns_bounded_multi_hop_paths(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(workspace["id"], "planning.md", "md", "content")
    chunks = repository.create_chunks(document["id"], workspace["id"], ["a", "b", "c", "d"])
    cards = [
        repository.create_knowledge_card(
            workspace_id=workspace["id"],
            source_document_id=document["id"],
            source_chunk_id=chunk["id"],
            card_type="decision",
            title=f"Card {index}",
            summary=f"Card {index}",
            evidence_quote=f"Card {index}",
            keywords=[f"card-{index}"],
            tags=[],
            status="proposed",
            confidence="medium",
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
    repository.create_relation(workspace["id"], cards[0]["id"], cards[1]["id"], "supports", "1 supports 2", "high")
    repository.create_relation(workspace["id"], cards[1]["id"], cards[2]["id"], "related_to", "2 relates 3", "medium")
    repository.create_relation(workspace["id"], cards[2]["id"], cards[3]["id"], "derived_from", "3 derives 4", "medium")

    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get(f"/api/workspaces/{workspace['id']}/cards/{cards[0]['id']}/paths", params={"depth": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["start_card_id"] == cards[0]["id"]
    assert body["max_depth"] == 2
    assert all(path["depth"] <= 2 for path in body["paths"])
    assert any(path["node_ids"] == [cards[0]["id"], cards[1]["id"], cards[2]["id"]] for path in body["paths"])
    assert not any(cards[3]["id"] in path["node_ids"] for path in body["paths"])
    assert body["paths"][0]["edges"][0]["relation_type"] == "supports"


def test_card_paths_api_returns_404_for_missing_card(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "SOMA 49"}).json()["id"]

    response = client.get(f"/api/workspaces/{workspace_id}/cards/999/paths", params={"depth": 2})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
