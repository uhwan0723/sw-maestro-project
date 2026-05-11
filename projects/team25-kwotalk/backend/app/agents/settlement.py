"""settlement_node — retrieved_docs 의 사례에서 합의금 통계."""
from statistics import median

from app.state import LegalState

MIN_RELIABLE_SAMPLES = 5


async def settlement_node(state: LegalState) -> dict:
    if not state.get("needs_settlement"):
        return {"settlement": None}

    amounts: list[int] = []
    for doc in state.get("retrieved_docs", []) or []:
        if doc.get("type") != "사례":
            continue
        amt = doc.get("settlement_amount")
        if isinstance(amt, (int, float)) and amt > 0:
            amounts.append(int(amt))

    if not amounts:
        return {"settlement": None}

    n = len(amounts)
    basis = (
        f"검색된 유사 사례 {n}건의 합의금 통계"
        if n >= MIN_RELIABLE_SAMPLES
        else f"검색된 유사 사례 {n}건 (표본 부족, 참고용)"
    )

    return {
        "settlement": {
            "min": min(amounts),
            "median": int(median(amounts)),
            "max": max(amounts),
            "sample_size": n,
            "basis": basis,
        }
    }
