from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.consultation import ClassifiedItem, Classify2Payload


CONSENSUS_SKIP_THRESHOLD = 0.7


def normalize_classify_payload(
    payload: Classify2Payload,
    *,
    valid_message_ids: set[str],
) -> Classify2Payload:
    _validate_supporting_ids(payload, valid_message_ids=valid_message_ids)
    if not payload.consensus and not payload.conflict and not payload.pending:
        payload = payload.model_copy(
            update={
                "pending": [ClassifiedItem(topic="미도출", supporting_message_ids=[])],
                "consensus_ratio": 0.0,
                "next_action": "proceed_to_round_3",
            }
        )
    payload = _recompute_consensus_ratio(payload)
    if not should_skip_to_final(payload):
        payload = payload.model_copy(update={"next_action": "proceed_to_round_3"})
    return payload


def _recompute_consensus_ratio(payload: Classify2Payload) -> Classify2Payload:
    """Override the LLM-reported ratio with the spec formula.

    spec §4.2: consensus_ratio = consensus / (consensus + conflict + pending),
    rounded to two decimals. The LLM frequently miscounts (e.g. de-duplicating one
    side but not the other), so we treat this as a derived field owned by the backend.
    """

    total = len(payload.consensus) + len(payload.conflict) + len(payload.pending)
    expected = round(len(payload.consensus) / total, 2) if total > 0 else 0.0
    if abs(payload.consensus_ratio - expected) <= 0.005:
        return payload
    return payload.model_copy(update={"consensus_ratio": expected})


def should_skip_to_final(payload: Classify2Payload | Mapping[str, Any]) -> bool:
    data = payload.model_dump(mode="json") if isinstance(payload, Classify2Payload) else payload
    consensus = data.get("consensus") or []
    conflict = data.get("conflict") or []
    consensus_ratio = float(data.get("consensus_ratio") or 0.0)
    return (
        data.get("next_action") == "skip_to_final"
        and consensus_ratio >= CONSENSUS_SKIP_THRESHOLD
        and len(conflict) == 0
        and len(consensus) > 0
        and any(item.get("supporting_message_ids") for item in consensus if isinstance(item, dict))
    )


def _validate_supporting_ids(
    payload: Classify2Payload,
    *,
    valid_message_ids: set[str],
) -> None:
    invalid_ids = sorted(
        {
            message_id
            for item in [*payload.consensus, *payload.conflict, *payload.pending]
            for message_id in item.supporting_message_ids
            if message_id not in valid_message_ids
        }
    )
    if invalid_ids:
        raise ValueError(f"classify_2 contains unknown supporting_message_ids: {invalid_ids}")
