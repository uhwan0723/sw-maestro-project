"""답변 본문에서 [N] 마커를 추출해 retrieved_docs 와 매핑."""
import logging
import re

from app.state import Citation, RetrievedDoc

logger = logging.getLogger(__name__)

_MARKER_RE = re.compile(r"\[(\d+)\]")


def extract_citations(
    answer_text: str,
    retrieved_docs: list[RetrievedDoc],
) -> list[Citation]:
    """본문 [N] 패턴을 retrieved_docs[N-1].doc_id 와 매핑.

    중복 제거. 미사용·범위 밖 마커는 무시 (로깅).
    """
    seen: set[int] = set()
    citations: list[Citation] = []

    for match in _MARKER_RE.finditer(answer_text):
        idx = int(match.group(1))
        if idx in seen:
            continue
        seen.add(idx)

        if idx < 1 or idx > len(retrieved_docs):
            logger.warning("인용 마커 [%d]가 범위를 벗어남 (docs=%d개)", idx, len(retrieved_docs))
            continue

        citations.append(Citation(marker_idx=idx, doc_id=retrieved_docs[idx - 1]["doc_id"]))

    return citations
