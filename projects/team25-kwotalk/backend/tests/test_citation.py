"""citation_extractor 단위 테스트."""
import logging

from app.state import RetrievedDoc
from app.utils.citation_extractor import extract_citations


def _make_docs(n: int) -> list[RetrievedDoc]:
    return [
        {
            "doc_id": f"doc_{i:03d}",
            "type": "법령",
            "title": f"법령 {i}",
            "content": f"내용 {i}",
            "case_types": [],
            "score": 0.9,
            "settlement_amount": None,
        }
        for i in range(1, n + 1)
    ]


def test_extract_basic():
    """본문 [1], [2] → citations 2개 추출."""
    text = "관련 법령은 [1]을 참조하며, 판례 [2]에 따르면..."
    docs = _make_docs(3)
    result = extract_citations(text, docs)

    assert len(result) == 2
    assert result[0]["marker_idx"] == 1
    assert result[0]["doc_id"] == "doc_001"
    assert result[1]["marker_idx"] == 2
    assert result[1]["doc_id"] == "doc_002"


def test_extract_dedupe():
    """동일 마커 중복 등장 시 1번만 기록."""
    text = "[1] 관련 내용, 또한 [1]에서 확인 가능합니다."
    docs = _make_docs(2)
    result = extract_citations(text, docs)

    assert len(result) == 1
    assert result[0]["marker_idx"] == 1


def test_extract_out_of_range(caplog):
    """[5] 마커인데 retrieved_docs 가 3개면 무시 + 경고 로그."""
    text = "[1] 참고, [5] 참고"
    docs = _make_docs(3)

    with caplog.at_level(logging.WARNING, logger="app.utils.citation_extractor"):
        result = extract_citations(text, docs)

    assert len(result) == 1
    assert result[0]["marker_idx"] == 1
    assert any("범위를 벗어남" in msg for msg in caplog.messages)


def test_extract_no_markers():
    """마커 없는 본문 → 빈 리스트."""
    text = "이 답변에는 인용이 없습니다."
    docs = _make_docs(2)
    result = extract_citations(text, docs)
    assert result == []


def test_extract_empty_docs():
    """retrieved_docs 가 비어있으면 모든 마커를 무시."""
    text = "[1] [2] [3]"
    result = extract_citations(text, [])
    assert result == []
