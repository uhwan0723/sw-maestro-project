from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.errors import to_public_error
from app.logging_utils import include_traceback_in_logs, redact_for_log
from app.schemas.consultation import (
    AGENT_NAMES,
    ROUND_1_AGENT_ORDER,
    SEQUENTIAL_AGENT_ORDER,
    ActionItem,
    AgentFinalPosition,
    AgentId,
    AgentOpinion,
    AgentRebuttal,
    ConsultationState,
    ConsultationStatus,
    ErrorCode,
    ErrorEvent,
    FinalPayload,
    RoundType,
    SkippedAgent,
    Termination,
    TerminationReason,
    SupervisorNote,
    utc_now_iso,
)
from app.services.event_broker import EventBroker
from app.services.llm_client import LLMClient, LLMOutputError
from app.store.memory import MemoryStore
from app.workflow.classification import normalize_classify_payload
from app.workflow.state import build_consultation_response
from pydantic import ValidationError


logger = logging.getLogger(__name__)


ROUND_SURVIVAL_THRESHOLD = 4
ROUND_TIMEOUT_SECONDS = 120.0


class RoundSurvivalError(RuntimeError):
    """Raised when a round produces fewer than ROUND_SURVIVAL_THRESHOLD survivors."""

    def __init__(self, round_type: RoundType, survived: int, total: int) -> None:
        self.round_type = round_type
        self.survived = survived
        self.total = total
        super().__init__(
            f"insufficient {round_type.value} survivors: {survived}/{total} "
            f"(need >= {ROUND_SURVIVAL_THRESHOLD})"
        )


class RoundTimeoutError(RuntimeError):
    """Raised when a round exceeds ROUND_TIMEOUT_SECONDS."""

    def __init__(self, round_type: RoundType) -> None:
        self.round_type = round_type
        super().__init__(
            f"{round_type.value} exceeded {ROUND_TIMEOUT_SECONDS:.0f}s round timeout"
        )


class WorkflowTimeoutError(RuntimeError):
    """Raised when the entire workflow exceeds the configured deadline."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"workflow exceeded {timeout_seconds:.0f}s timeout")


class WorkflowNodes:
    def __init__(self, store: MemoryStore, broker: EventBroker, llm: LLMClient) -> None:
        self.store = store
        self.broker = broker
        self.llm = llm

    async def analyze_question(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ANALYZING)
        current = await self._require_state(consultation_id)
        analysis = await self.llm.analyze_question(consultation_id, current.user_question)

        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "analysis", analysis))
        await self.broker.publish(
            consultation_id,
            "analysis_completed",
            {"analysis": analysis.model_dump(mode="json")},
        )
        return {"analysis": analysis.model_dump(mode="json")}

    async def run_round_1(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_1_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None:
            raise RuntimeError("analysis is required before round_1")

        try:
            opinions = await asyncio.wait_for(
                self._run_round_1_body(consultation_id, current),
                timeout=ROUND_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise RoundTimeoutError(RoundType.ROUND_1) from exc

        if len(opinions) < ROUND_SURVIVAL_THRESHOLD:
            raise RoundSurvivalError(
                RoundType.ROUND_1, survived=len(opinions), total=len(ROUND_1_AGENT_ORDER)
            )

        return {"round_1_opinions": [opinion.model_dump(mode="json") for opinion in opinions]}

    async def _run_round_1_body(
        self, consultation_id: str, current: ConsultationState
    ) -> list[AgentOpinion]:
        results = await asyncio.gather(
            *[
                self.llm.create_agent_opinion(agent_id, current.user_question, current.analysis)
                for agent_id in ROUND_1_AGENT_ORDER
            ],
            return_exceptions=True,
        )

        opinions: list[AgentOpinion] = []
        for agent_id, result in zip(ROUND_1_AGENT_ORDER, results, strict=True):
            if isinstance(result, BaseException):
                await self._record_skipped_agent(
                    consultation_id, agent_id, RoundType.ROUND_1, result
                )
                continue
            try:
                opinion = AgentOpinion(
                    consultation_id=consultation_id,
                    agent_id=agent_id,
                    agent_name=AGENT_NAMES[agent_id],
                    **result.model_dump(),
                )
            except Exception as exc:
                await self._record_skipped_agent(
                    consultation_id, agent_id, RoundType.ROUND_1, exc
                )
                continue
            opinions.append(opinion)

        if opinions:
            async def mutate(stored: ConsultationState) -> None:
                stored.round_1_opinions.extend(opinions)

            await self.store.mutate(consultation_id, mutate)
            for opinion in opinions:
                await self.broker.publish(
                    consultation_id,
                    "agent_message_added",
                    {"round": "round_1", "message": opinion.model_dump(mode="json")},
                )

        return opinions

    async def summarize_round_1(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.SUMMARY_1_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None:
            raise RuntimeError("analysis is required before summary_1")
        payload = await self.llm.summarize_round_1(
            current.user_question,
            current.analysis,
            current.round_1_opinions,
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="summary_1",
            payload=payload.model_dump(mode="json"),
        )
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "summary_1", note))
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        return {"summary_1": note.model_dump(mode="json")}

    async def run_round_2(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_2_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None or current.summary_1 is None:
            raise RuntimeError("analysis and summary_1 are required before round_2")

        try:
            rebuttals = await asyncio.wait_for(
                self._run_round_2_body(consultation_id, current),
                timeout=ROUND_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise RoundTimeoutError(RoundType.ROUND_2) from exc

        if len(rebuttals) < ROUND_SURVIVAL_THRESHOLD:
            raise RoundSurvivalError(
                RoundType.ROUND_2, survived=len(rebuttals), total=len(SEQUENTIAL_AGENT_ORDER)
            )

        return {"round_2_rebuttals": [item.model_dump(mode="json") for item in rebuttals]}

    async def _run_round_2_body(
        self, consultation_id: str, current: ConsultationState
    ) -> list[AgentRebuttal]:
        rebuttals: list[AgentRebuttal] = []

        for agent_id in SEQUENTIAL_AGENT_ORDER:
            try:
                draft = await self.llm.create_agent_rebuttal(
                    agent_id,
                    current.user_question,
                    current.analysis,
                    current.summary_1,
                    current.round_1_opinions,
                    rebuttals,
                )
                rebuttal = AgentRebuttal(
                    consultation_id=consultation_id,
                    agent_id=agent_id,
                    agent_name=AGENT_NAMES[agent_id],
                    **draft.model_dump(),
                )
                self._validate_rebuttal_targets(rebuttal, current.round_1_opinions)
            except Exception as exc:
                await self._record_skipped_agent(
                    consultation_id, agent_id, RoundType.ROUND_2, exc
                )
                continue
            rebuttals.append(rebuttal)

            async def mutate(stored: ConsultationState, item: AgentRebuttal = rebuttal) -> None:
                stored.round_2_rebuttals.append(item)

            await self.store.mutate(consultation_id, mutate)
            await self.broker.publish(
                consultation_id,
                "agent_message_added",
                {"round": "round_2", "message": rebuttal.model_dump(mode="json")},
            )

        return rebuttals

    async def classify_round_2(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.CLASSIFY_2_RUNNING)
        current = await self._require_state(consultation_id)
        if current.summary_1 is None:
            raise RuntimeError("summary_1 is required before classify_2")
        payload = await self.llm.classify_round_2(current.summary_1, current.round_2_rebuttals)
        payload = normalize_classify_payload(
            payload,
            valid_message_ids={
                item.id for item in [*current.round_1_opinions, *current.round_2_rebuttals]
            },
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="classify_2",
            payload=payload.model_dump(mode="json"),
        )
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "classify_2", note))
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        return {"classify_2": note.model_dump(mode="json")}

    async def mark_consensus_reached(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        termination = Termination(
            reason=TerminationReason.CONSENSUS_REACHED,
            occurred_at=utc_now_iso(),
            notes="classify_2.payload.next_action == skip_to_final",
        )
        await self.store.mutate(
            consultation_id,
            lambda stored: setattr(stored, "termination", termination),
        )
        return {"termination": termination.model_dump(mode="json")}

    async def run_round_3(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_3_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None or current.summary_1 is None or current.classify_2 is None:
            raise RuntimeError("analysis, summary_1, and classify_2 are required before round_3")

        try:
            positions = await asyncio.wait_for(
                self._run_round_3_body(consultation_id, current),
                timeout=ROUND_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise RoundTimeoutError(RoundType.ROUND_3) from exc

        return {"round_3_positions": [item.model_dump(mode="json") for item in positions]}

    async def _run_round_3_body(
        self, consultation_id: str, current: ConsultationState
    ) -> list[AgentFinalPosition]:
        positions: list[AgentFinalPosition] = []

        for agent_id in SEQUENTIAL_AGENT_ORDER:
            if any(skipped.agent_id == agent_id for skipped in current.skipped_agents):
                continue
            try:
                own_round_1 = self._find_opinion(current.round_1_opinions, agent_id)
                draft = await self.llm.create_agent_final_position(
                    agent_id,
                    current.user_question,
                    current.analysis,
                    current.summary_1,
                    current.classify_2,
                    own_round_1,
                    self._find_rebuttal(current.round_2_rebuttals, agent_id),
                    positions,
                )
                draft = _normalize_changed_from_round_1(draft, own_round_1)
                position = AgentFinalPosition(
                    consultation_id=consultation_id,
                    agent_id=agent_id,
                    agent_name=AGENT_NAMES[agent_id],
                    **draft.model_dump(),
                )
            except Exception as exc:
                await self._record_skipped_agent(
                    consultation_id, agent_id, RoundType.ROUND_3, exc
                )
                continue
            positions.append(position)

            async def mutate(stored: ConsultationState, item: AgentFinalPosition = position) -> None:
                stored.round_3_positions.append(item)

            await self.store.mutate(consultation_id, mutate)
            await self.broker.publish(
                consultation_id,
                "agent_message_added",
                {"round": "round_3", "message": position.model_dump(mode="json")},
            )

        return positions

    async def finalize(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.SUMMARIZING)
        current = await self._require_state(consultation_id)
        payload = await self.llm.create_final_summary(
            current.user_question,
            current.analysis,
            current.summary_1,
            current.classify_2,
            current.round_3_positions,
            current.round_2_rebuttals,
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="final",
            payload=payload.model_dump(mode="json"),
        )

        async def mutate(stored: ConsultationState) -> None:
            stored.final_summary = note
            stored.status = (
                ConsultationStatus.TERMINATED
                if stored.termination is not None
                else ConsultationStatus.COMPLETED
            )
            stored.completed_at = stored.updated_at

        updated, _ = await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "status_changed",
            {"status": updated.status.value},
        )
        await self.broker.publish(
            consultation_id,
            "completed",
            {"response": build_consultation_response(updated).model_dump(mode="json")},
        )
        return {
            "final_summary": note.model_dump(mode="json"),
            "status": updated.status.value,
            "completed_at": updated.completed_at,
        }

    async def handle_failure(self, consultation_id: str, exc: Exception) -> None:
        error = _error_event_from_exception(exc)
        termination = _termination_from_exception(exc)

        if termination is not None and termination.reason in _FALLBACK_FINAL_REASONS:
            try:
                await self._terminate_with_final_fallback(consultation_id, error, termination)
                return
            except Exception as fallback_exc:
                logger.warning(
                    "fallback integrate_final failed; downgrading to FAILED",
                    extra={
                        "consultation_id": consultation_id,
                        "termination_reason": termination.reason.value,
                        "fallback_error": redact_for_log(str(fallback_exc), max_len=120),
                    },
                )

        log_kwargs: dict[str, Any] = {
            "extra": {
                "consultation_id": consultation_id,
                "error_code": error.code.value,
                "where": error.where,
                "retry_count": error.retry_count,
                "detail_length": len(error.detail or ""),
            },
        }
        if include_traceback_in_logs():
            log_kwargs["exc_info"] = (type(exc), exc, exc.__traceback__)
        logger.error("consultation workflow failed", **log_kwargs)

        async def mutate(stored: ConsultationState) -> None:
            stored.errors.append(error)
            if termination is not None and stored.termination is None:
                stored.termination = termination
            stored.status = ConsultationStatus.FAILED
            stored.completed_at = stored.updated_at

        updated, _ = await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "error_occurred",
            {"error": to_public_error(error).model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "status_changed",
            {"status": ConsultationStatus.FAILED.value},
        )
        await self.broker.publish(
            consultation_id,
            "completed",
            {"response": build_consultation_response(updated).model_dump(mode="json")},
        )

    async def _terminate_with_final_fallback(
        self,
        consultation_id: str,
        error: ErrorEvent,
        termination: Termination,
    ) -> None:
        current = await self._require_state(consultation_id)
        if current.analysis is None:
            raise RuntimeError(
                "cannot integrate_final without analysis; downgrade to FAILED"
            )

        try:
            payload: FinalPayload = await asyncio.wait_for(
                self.llm.create_final_summary(
                    current.user_question,
                    current.analysis,
                    current.summary_1,
                    current.classify_2,
                    current.round_3_positions,
                    current.round_2_rebuttals,
                ),
                timeout=ROUND_TIMEOUT_SECONDS,
            )
        except Exception as llm_exc:
            logger.warning(
                "fallback final LLM call failed; using static fallback payload",
                extra={
                    "consultation_id": consultation_id,
                    "termination_reason": termination.reason.value,
                    "llm_error": redact_for_log(str(llm_exc), max_len=120),
                },
            )
            payload = _static_fallback_final_payload()

        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="final",
            payload=payload.model_dump(mode="json"),
        )

        async def mutate(stored: ConsultationState) -> None:
            stored.errors.append(error)
            if stored.termination is None:
                stored.termination = termination
            stored.final_summary = note
            stored.status = ConsultationStatus.TERMINATED
            stored.completed_at = stored.updated_at

        updated, _ = await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "error_occurred",
            {"error": to_public_error(error).model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "status_changed",
            {"status": ConsultationStatus.TERMINATED.value},
        )
        await self.broker.publish(
            consultation_id,
            "completed",
            {"response": build_consultation_response(updated).model_dump(mode="json")},
        )

    async def _record_skipped_agent(
        self,
        consultation_id: str,
        agent_id: AgentId,
        round_type: RoundType,
        exc: BaseException,
    ) -> None:
        error = _agent_error_event_from_exception(exc, agent_id, round_type)
        skipped = SkippedAgent(
            agent_id=agent_id,
            round=round_type,
            reason=error.code,
            occurred_at=utc_now_iso(),
        )

        async def mutate(stored: ConsultationState) -> None:
            stored.errors.append(error)
            stored.skipped_agents.append(skipped)

        await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "error_occurred",
            {"error": to_public_error(error).model_dump(mode="json")},
        )
        logger.warning(
            "skipped agent during round",
            extra={
                "consultation_id": consultation_id,
                "agent_id": agent_id.value,
                "round": round_type.value,
                "error_code": error.code.value,
            },
        )

    async def _set_status(self, consultation_id: str, status: ConsultationStatus) -> None:
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "status", status))
        await self.broker.publish(consultation_id, "status_changed", {"status": status.value})

    async def _require_state(self, consultation_id: str) -> ConsultationState:
        state = await self.store.get(consultation_id)
        if state is None:
            raise RuntimeError(f"consultation not found: {consultation_id}")
        return state

    @staticmethod
    def _validate_rebuttal_targets(
        rebuttal: AgentRebuttal,
        round_1_opinions: list[AgentOpinion],
    ) -> None:
        opinions_by_id = {opinion.id: opinion for opinion in round_1_opinions}
        for target in rebuttal.targets:
            opinion = opinions_by_id.get(target.target_message_id)
            if opinion is None:
                raise ValueError(f"unknown target_message_id: {target.target_message_id}")
            if opinion.agent_id != target.target_agent_id:
                raise ValueError(
                    "target_agent_id does not match target_message_id: "
                    f"{target.target_agent_id} != {opinion.agent_id}"
                )

    @staticmethod
    def _find_opinion(opinions: list[AgentOpinion], agent_id: AgentId) -> AgentOpinion | None:
        return next((opinion for opinion in opinions if opinion.agent_id == agent_id), None)

    @staticmethod
    def _find_rebuttal(rebuttals: list[AgentRebuttal], agent_id: AgentId) -> AgentRebuttal | None:
        return next((rebuttal for rebuttal in rebuttals if rebuttal.agent_id == agent_id), None)


def _error_event_from_exception(exc: Exception) -> ErrorEvent:
    if isinstance(exc, RoundSurvivalError):
        return ErrorEvent(
            code=ErrorCode.UNKNOWN,
            where=f"workflow:{exc.round_type.value}_survival",
            detail=str(exc),
            fatal=True,
        )

    if isinstance(exc, RoundTimeoutError):
        return ErrorEvent(
            code=ErrorCode.WORKFLOW_TIMEOUT,
            where=f"workflow:{exc.round_type.value}_timeout",
            detail=str(exc),
            fatal=True,
        )

    if isinstance(exc, WorkflowTimeoutError):
        return ErrorEvent(
            code=ErrorCode.WORKFLOW_TIMEOUT,
            where="workflow:timeout",
            detail=str(exc),
            fatal=True,
        )

    if isinstance(exc, LLMOutputError):
        return ErrorEvent(
            code=exc.code,
            where=f"llm:{exc.task}",
            detail=exc.detail,
            retry_count=exc.retry_count,
            fatal=True,
        )

    if isinstance(exc, ValidationError):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where="workflow:schema_validation",
            detail=str(exc),
            fatal=True,
        )

    detail = str(exc)
    if _is_schema_boundary_error(detail):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where=_infer_schema_error_where(detail),
            detail=detail,
            fatal=True,
        )

    return ErrorEvent(
        code=ErrorCode.UNKNOWN,
        where="workflow",
        detail=detail,
        fatal=True,
    )


def _agent_error_event_from_exception(
    exc: BaseException, agent_id: AgentId, round_type: RoundType
) -> ErrorEvent:
    where = f"round:{round_type.value}:agent_{agent_id.value}"
    if isinstance(exc, LLMOutputError):
        return ErrorEvent(
            code=exc.code,
            where=where,
            detail=exc.detail,
            retry_count=exc.retry_count,
            fatal=False,
        )
    if isinstance(exc, ValidationError):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where=where,
            detail=str(exc),
            fatal=False,
        )
    detail = str(exc)
    if _is_schema_boundary_error(detail):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where=where,
            detail=detail,
            fatal=False,
        )
    return ErrorEvent(
        code=ErrorCode.UNKNOWN,
        where=where,
        detail=detail,
        fatal=False,
    )


def _termination_from_exception(exc: BaseException) -> Termination | None:
    if isinstance(exc, RoundSurvivalError):
        return Termination(
            reason=TerminationReason.INTERNAL_ERROR,
            occurred_at=utc_now_iso(),
            notes=str(exc),
        )
    if isinstance(exc, (RoundTimeoutError, WorkflowTimeoutError)):
        return Termination(
            reason=TerminationReason.TIMEOUT,
            occurred_at=utc_now_iso(),
            notes=str(exc),
        )
    return None


_FALLBACK_FINAL_REASONS: frozenset[TerminationReason] = frozenset(
    {
        TerminationReason.TIMEOUT,
        TerminationReason.REPETITION_DETECTED,
        TerminationReason.ROUND_LIMIT_EXCEEDED,
        TerminationReason.PERSONA_BREAKDOWN,
    }
)


_DEFAULT_CHANGE_REASON = "토론 결과를 반영해 입장을 조정했습니다."


def _normalize_changed_from_round_1(draft, own_round_1_opinion: AgentOpinion | None):
    """Make `changed_from_round_1` and `change_reason` consistent with the actual stance diff.

    LLMs frequently misreport whether their final stance differs from round_1 (observed
    rate ~67% on real runs). The boolean is fully derivable from comparing the two
    stance enums, so we recompute it here instead of trusting the LLM. ``change_reason``
    is kept when the recomputation confirms a change, and cleared otherwise; if the LLM
    failed to provide a reason despite an actual change, we fall back to a generic note.
    """

    if own_round_1_opinion is None:
        return draft
    actually_changed = own_round_1_opinion.stance != draft.final_stance
    if actually_changed:
        reason_consistent = bool(draft.change_reason)
    else:
        reason_consistent = draft.change_reason is None
    if actually_changed == draft.changed_from_round_1 and reason_consistent:
        return draft
    update: dict[str, Any] = {"changed_from_round_1": actually_changed}
    if actually_changed:
        update["change_reason"] = draft.change_reason or _DEFAULT_CHANGE_REASON
    else:
        update["change_reason"] = None
    return draft.model_copy(update=update)


def _static_fallback_final_payload() -> FinalPayload:
    """Used when handle_failure cannot reach the LLM but still wants to deliver a final."""

    return FinalPayload(
        situation=(
            "상담을 진행하던 도중 시간이 길어져 지금까지 정리된 의견을 그대로 전달드립니다."
        ),
        disagreements=[],
        final_advice=(
            "지금까지 모인 의견을 참고해 천천히 다음 행동을 결정해 보세요. "
            "필요하다면 잠시 뒤에 다시 상담을 시작해도 좋습니다."
        ),
        action_items=[
            ActionItem(
                title="현재 정리된 의견 다시 살펴보기",
                detail="에이전트들이 남긴 의견과 핵심 포인트를 짧게 메모해 두세요.",
                timing="immediate",
            ),
        ],
        caveats=["이 답변은 전문 심리상담을 대체하지 않습니다."],
    )


def _is_schema_boundary_error(detail: str) -> bool:
    schema_error_markers = (
        "unknown target_message_id",
        "target_agent_id does not match target_message_id",
        "supporting_message_ids",
        "validation error",
    )
    return any(marker in detail for marker in schema_error_markers)


def _infer_schema_error_where(detail: str) -> str:
    if "target_message_id" in detail or "target_agent_id" in detail:
        return "workflow:round_2_target_reference"
    if "supporting_message_ids" in detail:
        return "workflow:classify_2_supporting_ids"
    return "workflow:schema_validation"
