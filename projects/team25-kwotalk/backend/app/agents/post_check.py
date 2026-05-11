"""post_check_node — 룰 기반 신뢰도 점수 + 변호사 권유 분기."""
from app.agents.settlement import MIN_RELIABLE_SAMPLES
from app.state import LegalState


def _score(state: LegalState) -> float:
    cls_conf = float(state.get("classification_confidence", 0.0))
    docs = state.get("retrieved_docs", []) or []
    cites = state.get("citations", []) or []

    doc_score = min(len(docs) / 3.0, 1.0)
    cite_score = min(len(cites) / 2.0, 1.0)
    avg_doc_score = (
        sum(d.get("score", 0.0) for d in docs) / len(docs) if docs else 0.0
    )

    return round(
        0.35 * cls_conf
        + 0.25 * doc_score
        + 0.20 * cite_score
        + 0.20 * avg_doc_score,
        3,
    )


async def post_check_node(state: LegalState) -> dict:
    score = _score(state)
    settlement = state.get("settlement")
    settlement_unreliable = bool(settlement) and settlement.get("sample_size", 0) < MIN_RELIABLE_SAMPLES

    recommend = (
        score < 0.55
        or float(state.get("classification_confidence", 1.0)) < 0.6
        or len(state.get("citations", []) or []) < 2
        or settlement_unreliable
    )

    return {
        "confidence_score": score,
        "recommend_lawyer": recommend,
    }
