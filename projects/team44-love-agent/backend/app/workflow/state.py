from __future__ import annotations

from typing import Any, TypedDict

from app.errors import to_public_error
from app.schemas.consultation import (
    AGENT_NAMES,
    AgentId,
    ConsultationResponse,
    ConsultationState,
    ConsultationStatus,
    PublicFinalSummary,
    PublicRound,
    PublicTermination,
    RoundType,
    TerminationReason,
    UserConsultationRequest,
    utc_now_iso,
)


_TERMINATION_USER_MESSAGE_KEY_OVERRIDES: dict[TerminationReason, str] = {
    TerminationReason.SAFETY_FILTER: "termination.safety_refused",
}


def _termination_user_message_key(reason: TerminationReason) -> str:
    override = _TERMINATION_USER_MESSAGE_KEY_OVERRIDES.get(reason)
    if override is not None:
        return override
    return f"termination.{reason.value}"


class ConsultationGraphState(TypedDict, total=False):
    consultation_id: str
    started_at: str
    updated_at: str
    status: str
    schema_version: str
    user_question: str
    language: str
    analysis: dict[str, Any]
    summary_1: dict[str, Any]
    classify_2: dict[str, Any]
    final_summary: dict[str, Any]
    round_1_opinions: list[dict[str, Any]]
    round_2_rebuttals: list[dict[str, Any]]
    round_3_positions: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    skipped_agents: list[dict[str, Any]]
    completed_at: str | None


def build_initial_state(request: UserConsultationRequest) -> ConsultationState:
    now = utc_now_iso()
    return ConsultationState(
        consultation_id=request.consultation_id,
        started_at=now,
        updated_at=now,
        status=ConsultationStatus.PENDING,
        user_question=request.user_question,
        language=request.language,
    )


def build_consultation_response(state: ConsultationState) -> ConsultationResponse:
    final = None
    if state.final_summary is not None:
        payload = state.final_summary.payload
        final = PublicFinalSummary(
            situation=payload["situation"],
            disagreements=payload.get("disagreements", []),
            final_advice=payload["final_advice"],
            action_items=payload.get("action_items", []),
            caveats=payload.get("caveats", []),
            contributing_agents=_contributing_agents(state),
        )

    termination = None
    if state.termination is not None:
        termination = PublicTermination(
            reason=state.termination.reason,
            user_message_key=_termination_user_message_key(state.termination.reason),
        )

    return ConsultationResponse(
        consultation_id=state.consultation_id,
        status=state.status,
        started_at=state.started_at,
        completed_at=state.completed_at,
        user_question=state.user_question,
        language=state.language,
        analysis=state.analysis,
        rounds=_public_rounds(state),
        final=final,
        termination=termination,
        errors=[to_public_error(error) for error in state.errors],
    )


def _public_rounds(state: ConsultationState) -> list[PublicRound]:
    rounds: list[PublicRound] = []

    if state.round_1_opinions:
        rounds.append(
            PublicRound(
                round=RoundType.ROUND_1,
                started_at=state.round_1_opinions[0].created_at,
                completed_at=state.round_1_opinions[-1].created_at,
                messages=state.round_1_opinions,
                supervisor_note=state.summary_1,
            )
        )
    if state.round_2_rebuttals:
        rounds.append(
            PublicRound(
                round=RoundType.ROUND_2,
                started_at=state.round_2_rebuttals[0].created_at,
                completed_at=state.round_2_rebuttals[-1].created_at,
                messages=state.round_2_rebuttals,
                supervisor_note=state.classify_2,
            )
        )
    if state.round_3_positions:
        rounds.append(
            PublicRound(
                round=RoundType.ROUND_3,
                started_at=state.round_3_positions[0].created_at,
                completed_at=state.round_3_positions[-1].created_at,
                messages=state.round_3_positions,
            )
        )

    return rounds


def _contributing_agents(state: ConsultationState) -> list[AgentId]:
    skipped = {item.agent_id for item in state.skipped_agents}
    agents = [agent for agent in AGENT_NAMES if agent is not AgentId.SUPERVISOR]
    return [agent for agent in agents if agent not in skipped]
