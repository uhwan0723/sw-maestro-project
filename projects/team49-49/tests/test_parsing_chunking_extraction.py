import pytest

from app.services.chunking import chunk_text, filter_reusable_chunks
from app.services.extraction import DeterministicCardExtractor, LLMCardExtractor
from app.services.parsing import parse_document


def test_parse_text_markdown_and_csv_bytes():
    assert parse_document("note.txt", "아이디어: 회의록을 카드로 저장".encode("utf-8")) == "아이디어: 회의록을 카드로 저장"
    assert parse_document("plan.md", "# 제목\n\n가설: 팀은 근거 검색이 필요하다".encode("utf-8")).startswith("# 제목")

    csv_text = parse_document("interview.csv", "name,pain\nA,회의 근거를 못 찾음\n".encode("utf-8"))

    assert "name" in csv_text
    assert "회의 근거를 못 찾음" in csv_text


def test_parse_document_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_document("audio.mp3", b"not supported")


def test_chunk_text_and_filter_reusable_chunks():
    text = "네 좋아요.\n\n가설: 사용자는 멘토링 전에 검증할 질문을 찾고 싶다.\n\nㅋㅋ 감사합니다."

    chunks = chunk_text(text, max_chars=80)
    filtered = filter_reusable_chunks(chunks)

    assert chunks == ["네 좋아요.", "가설: 사용자는 멘토링 전에 검증할 질문을 찾고 싶다.", "ㅋㅋ 감사합니다."]
    assert filtered == ["가설: 사용자는 멘토링 전에 검증할 질문을 찾고 싶다."]


def test_chunk_text_carries_markdown_heading_context():
    text = "# 5월 멘토링\n\n## 결정사항\n\nMVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.\n\n## 리스크\n\n관계가 많아지면 탐색 속도가 떨어질 수 있다."

    chunks = chunk_text(text, max_chars=120)
    filtered = filter_reusable_chunks(chunks)

    assert chunks == [
        "5월 멘토링\n결정사항\nMVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        "결정사항\n리스크\n관계가 많아지면 탐색 속도가 떨어질 수 있다.",
    ]
    assert filtered == chunks


def test_deterministic_extractor_creates_expected_card_types():
    extractor = DeterministicCardExtractor()
    chunk = "\n".join(
        [
            "아이디어: 멘토링 회의록을 Knowledge Card로 자동 정리한다.",
            "가설: 사용자는 같은 고민 반복을 줄이고 싶다.",
            "근거: 4월 회의록에서 결정 근거를 찾기 어렵다는 의견이 있었다.",
            "리스크: LLM이 근거 없는 답변을 만들 수 있다.",
            "결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
        ]
    )

    cards = extractor.extract(
        chunk=chunk,
        workspace_id=1,
        source_document_id=2,
        source_chunk_id=3,
    )

    assert [card.card_type for card in cards] == ["idea", "hypothesis", "evidence", "risk", "decision"]
    assert cards[0].title == "멘토링 회의록을 Knowledge Card로 자동 정리한다."
    assert cards[1].status == "needs_validation"
    assert cards[4].status == "decided"
    assert "GraphDB" in cards[4].keywords


def test_deterministic_extractor_handles_compact_labels_and_markdown_heading_context():
    extractor = DeterministicCardExtractor()

    cards = extractor.extract(
        chunk="결정: SQLite를 먼저 사용한다. 근거: 2주 안에 Neo4j 운영은 어렵다.\n\n리스크\n관계가 많아지면 multi-hop 검색이 느려질 수 있다.",
        workspace_id=1,
        source_document_id=2,
        source_chunk_id=3,
    )

    assert [card.card_type for card in cards] == ["decision", "evidence", "risk"]
    assert cards[0].summary == "SQLite를 먼저 사용한다."
    assert cards[1].summary == "2주 안에 Neo4j 운영은 어렵다."
    assert cards[2].summary == "관계가 많아지면 multi-hop 검색이 느려질 수 있다."


def test_deterministic_extractor_falls_back_to_needs_review_card():
    extractor = DeterministicCardExtractor()

    cards = extractor.extract(
        chunk="멘토 피드백에서 시장성과 구현 범위를 다시 정리하자는 이야기가 나왔다.",
        workspace_id=1,
        source_document_id=2,
        source_chunk_id=3,
    )

    assert len(cards) == 1
    assert cards[0].card_type == "question"
    assert cards[0].status == "needs_review"
    assert cards[0].confidence == "low"


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system_prompt: str, user_prompt: str):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.responses.pop(0) if self.responses else None


def test_llm_extractor_validates_json_schema_and_returns_cards():
    client = FakeLLMClient(
        [
            """
            {
              "cards": [
                {
                  "card_type": "decision",
                  "title": "SQLite 우선 사용",
                  "summary": "MVP에서는 SQLite를 먼저 사용한다.",
                  "evidence_quote": "SQLite를 먼저 사용한다는 결론이었다.",
                  "keywords": ["SQLite", "MVP"],
                  "tags": ["decided"],
                  "status": "decided",
                  "confidence": "high"
                }
              ]
            }
            """
        ]
    )

    cards = LLMCardExtractor(client).extract(
        chunk="SQLite를 먼저 사용한다는 결론이었다.",
        workspace_id=1,
        source_document_id=2,
        source_chunk_id=3,
    )

    assert cards[0].card_type == "decision"
    assert cards[0].workspace_id == 1
    assert cards[0].source_document_id == 2
    assert cards[0].source_chunk_id == 3
    assert "filter" in client.calls[0]["system_prompt"]
    assert "extract" in client.calls[0]["system_prompt"]
    assert "keyword" in client.calls[0]["system_prompt"]


def test_llm_extractor_retries_parse_failure_then_marks_needs_review():
    client = FakeLLMClient(["not json", '{"cards": [{"card_type": "unknown"}]}'])

    cards = LLMCardExtractor(client).extract(
        chunk="자연어 회의록",
        workspace_id=1,
        source_document_id=2,
        source_chunk_id=3,
    )

    assert len(client.calls) == 2
    assert cards[0].status == "needs_review"
    assert cards[0].confidence == "low"
