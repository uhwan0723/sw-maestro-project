from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections.abc import Callable
from typing import Protocol, TypeVar

LLM_CALL_TIMEOUT_SECONDS = 30.0

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.logging_utils import redact_for_log
from app.schemas.consultation import (
    AgentFinalPosition,
    AgentId,
    AGENT_NAMES,
    AgentOpinion,
    AgentRebuttal,
    AgreementType,
    Classify2Payload,
    ClassifiedItem,
    ErrorCode,
    FinalPayload,
    QuestionAnalysis,
    StanceType,
    Summary1Payload,
    TargetReference,
    ActionItem,
    SupervisorNote,
)
from app.services.prompts import PromptRegistry


T = TypeVar("T")
logger = logging.getLogger(__name__)


class LLMOutputError(ValueError):
    """Raised when an LLM response cannot be parsed or validated for a stage."""

    def __init__(
        self,
        *,
        code: ErrorCode,
        task: str,
        detail: str,
        retry_count: int = 0,
    ) -> None:
        self.code = code
        self.task = task
        self.detail = detail
        self.retry_count = retry_count
        retry_suffix = f" after {retry_count} retries" if retry_count else ""
        super().__init__(f"{code.value} during {task}{retry_suffix}: {detail}")


def _validate_items_max_length(values: list[str], *, max_length: int, field_name: str) -> list[str]:
    too_long = [index for index, value in enumerate(values) if len(value) > max_length]
    if too_long:
        raise ValueError(f"{field_name} items must be at most {max_length} characters")
    return values


class AgentOpinionDraft(BaseModel):
    advice: str = Field(min_length=1, max_length=700)
    rationale: str = Field(min_length=1, max_length=300)
    stance: StanceType
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str] = Field(min_length=1, max_length=3)

    @field_validator("key_points")
    @classmethod
    def validate_key_point_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=60, field_name="key_points")


class AgentRebuttalDraft(BaseModel):
    targets: list[TargetReference] = Field(min_length=1, max_length=3)
    statement: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=300)
    updated_position: StanceType | None = None
    new_evidence: list[str] = Field(default_factory=list, max_length=3)


class AgentFinalPositionDraft(BaseModel):
    final_stance: StanceType
    final_advice: str = Field(min_length=1, max_length=700)
    changed_from_round_1: bool
    change_reason: str | None = Field(default=None, max_length=200)
    action_items: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("action_items")
    @classmethod
    def validate_action_item_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=80, field_name="action_items")

    @model_validator(mode="after")
    def validate_change_reason_required(self) -> "AgentFinalPositionDraft":
        if self.changed_from_round_1 and not self.change_reason:
            raise ValueError("change_reason is required when changed_from_round_1 is true")
        return self


class LLMClient(Protocol):
    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        ...

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        ...

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        ...

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        round_1_opinions: list[AgentOpinion],
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        ...

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        ...

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        ...

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        ...


class MockLLMClient:
    """Schema-conformant mock used for local workflow/API/SSE validation."""

    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        return QuestionAnalysis(
            consultation_id=consultation_id,
            relationship_state="ambiguous",
            conflict_type="ambiguous",
            key_issues=[_short_issue(user_question), "상대방의 의도 확인 필요"],
            user_emotion="confused",
            debate_goal="상황을 단정하지 않고 다음 행동을 정한다.",
        )

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        templates = {
            AgentId.REALIST: ("관계의 신호를 행동 기준으로 확인하세요.", StanceType.CLARIFY),
            AgentId.EMPATH: ("불안을 혼자 키우지 말고 감정을 먼저 정리하세요.", StanceType.PAUSE),
            AgentId.ANALYST: ("패턴을 더 보고 단정은 피하세요.", StanceType.MIXED),
            AgentId.ACTOR: ("짧고 명확하게 만남이나 대화를 제안하세요.", StanceType.CLARIFY),
            AgentId.MEDIATOR: ("상대의 상황과 내 감정을 함께 고려하세요.", StanceType.MIXED),
            AgentId.FRIEND: ("너무 어렵게 돌리지 말고 편하게 물어봐도 됩니다.", StanceType.CLARIFY),
        }
        advice, stance = templates[agent_id]
        return AgentOpinionDraft(
            advice=advice,
            rationale=f"질문 핵심은 '{analysis.key_issues[0]}'이며, 지금은 정보가 부족합니다.",
            stance=stance,
            confidence=0.72,
            key_points=["단정 금지", "직접 확인", "감정 보호"],
        )

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        return Summary1Payload(
            headline="대부분의 의견은 단정보다 확인과 감정 보호에 모입니다.",
            converging_points=["상대 의도 단정 금지", "직접 확인 필요"],
            diverging_points=["바로 행동할지 조금 더 볼지"],
            open_questions=["어떤 방식으로 부담 없이 확인할 수 있을까?"],
        )

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        round_1_opinions: list[AgentOpinion],
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        templates = {
            AgentId.REALIST: {
                "target_agent_id": AgentId.EMPATH,
                "agreement": AgreementType.PARTIAL,
                "statement": "{target_name}님의 감정을 먼저 돌보자는 의견은 필요합니다. 다만 지금은 위로만으로 끝내면 답장 간격이나 만남 제안에 대한 실제 반응을 놓칠 수 있으니, 사용자가 확인할 행동 기준까지 함께 정해야 합니다.",
                "rationale": "감정 보호와 사실 확인이 같이 있어야 사용자가 같은 불안을 반복하지 않습니다.",
                "updated_position": StanceType.CLARIFY,
                "new_evidence": ["연락 빈도와 실제 만남 반응을 함께 확인", "위로와 행동 기준을 함께 제시"],
            },
            AgentId.ANALYST: {
                "target_agent_id": AgentId.ACTOR,
                "agreement": AgreementType.EXTEND,
                "statement": "{target_name}님의 바로 대화를 제안하자는 의견은 실행력이 있다는 점에서 좋습니다. 다만 최근 연락 빈도, 답장 톤, 만남 약속의 변화가 함께 정리되지 않으면 행동이 너무 급하게 느껴질 수 있습니다.",
                "rationale": "대화 제안 전에 관찰된 패턴을 정리하면 상대의 반응을 더 정확하게 해석할 수 있습니다.",
                "updated_position": StanceType.MIXED,
                "new_evidence": ["최근 패턴 비교 후 확인", "행동 전에 관찰 근거 정리"],
            },
            AgentId.MEDIATOR: {
                "target_agent_id": AgentId.REALIST,
                "agreement": AgreementType.PARTIAL,
                "statement": "{target_name}님의 행동 기준을 세우자는 의견은 현실적입니다. 하지만 그 기준이 상대를 평가하는 체크리스트처럼 들리면 대화가 방어적으로 흐를 수 있으니, 내 감정과 상대 상황을 함께 묻는 표현으로 바꿔야 합니다.",
                "rationale": "확인 질문이 한쪽의 책임 추궁처럼 들리지 않아야 서로의 사정을 같이 볼 수 있습니다.",
                "updated_position": StanceType.MIXED,
                "new_evidence": ["내 감정과 상대 상황을 함께 묻기", "평가보다 대화 중심 표현 사용"],
            },
            AgentId.EMPATH: {
                "target_agent_id": AgentId.ANALYST,
                "agreement": AgreementType.EXTEND,
                "statement": "{target_name}님의 패턴을 더 보자는 의견은 성급한 판단을 막아줍니다. 그런데 기다리는 시간이 길어질수록 사용자의 불안이 커질 수 있으니, 관찰 기간과 함께 마음을 진정시키는 기준도 같이 정해야 합니다.",
                "rationale": "분석만 계속하면 사용자가 더 지칠 수 있어 감정 소모를 줄이는 장치가 필요합니다.",
                "updated_position": StanceType.PAUSE,
                "new_evidence": ["기다리는 동안의 감정 소모 관리", "관찰 기간을 미리 제한"],
            },
            AgentId.ACTOR: {
                "target_agent_id": AgentId.MEDIATOR,
                "agreement": AgreementType.DISAGREE,
                "statement": "{target_name}님의 양쪽을 함께 보자는 의견은 조심스럽고 안전합니다. 하지만 너무 오래 균형만 잡다 보면 결정을 미루게 되니, 오늘 보낼 수 있는 짧은 확인 메시지처럼 바로 실행할 행동이 필요합니다.",
                "rationale": "불확실성이 길어질수록 사용자의 에너지가 더 많이 소모되므로 작은 행동으로 상황을 움직여야 합니다.",
                "updated_position": StanceType.CLARIFY,
                "new_evidence": ["짧은 확인 메시지 작성", "오늘 실행 가능한 행동 선택"],
            },
            AgentId.FRIEND: {
                "target_agent_id": AgentId.ACTOR,
                "agreement": AgreementType.PARTIAL,
                "statement": "{target_name}님의 명확하게 대화를 제안하자는 의견은 답답함을 줄여줍니다. 다만 말이 너무 진지하게 시작되면 상대가 부담을 느낄 수 있으니, 평소 말투로 가볍게 근황과 마음을 물어보는 편이 자연스럽습니다.",
                "rationale": "관계가 아직 애매할수록 부담 없는 톤이 대화를 시작하기 쉽고, 상대도 방어적으로 반응할 가능성이 낮습니다.",
                "updated_position": StanceType.CLARIFY,
                "new_evidence": ["평소 말투로 가볍게 확인", "진지한 추궁보다 자연스러운 질문"],
            },
        }
        template = templates[agent_id]
        preferred_target_agent_id = template["target_agent_id"]
        target_opinion = next(
            (
                opinion
                for opinion in round_1_opinions
                if opinion.agent_id == preferred_target_agent_id
            ),
            None,
        )
        target_opinion = target_opinion or next(
            (opinion for opinion in round_1_opinions if opinion.agent_id != agent_id),
            round_1_opinions[0] if round_1_opinions else None,
        )
        if target_opinion is None:
            raise LLMOutputError(
                code=ErrorCode.SCHEMA_VIOLATION,
                task=f"round_2.{agent_id.value}",
                detail="round_1_opinions is empty; cannot build a target reference",
            )
        target_name = AGENT_NAMES[target_opinion.agent_id]
        return AgentRebuttalDraft(
            targets=[
                TargetReference(
                    target_message_id=target_opinion.id,
                    target_agent_id=target_opinion.agent_id,
                    agreement=template["agreement"],
                )
            ],
            statement=template["statement"].format(target_name=target_name),
            rationale=template["rationale"],
            updated_position=template["updated_position"],
            new_evidence=template["new_evidence"],
        )

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        rebuttal_ids = [item.id for item in round_2_rebuttals]
        return Classify2Payload(
            consensus=[
                ClassifiedItem(topic="상대 의도는 직접 확인해야 한다", supporting_message_ids=rebuttal_ids[:3])
            ],
            conflict=[
                ClassifiedItem(topic="바로 행동할지 시간을 둘지", supporting_message_ids=rebuttal_ids[3:5])
            ],
            pending=[
                ClassifiedItem(topic="상대의 실제 상황 정보 부족", supporting_message_ids=rebuttal_ids[5:])
            ],
            consensus_ratio=0.66,
            next_action="proceed_to_round_3",
        )

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        templates = {
            AgentId.REALIST: {
                "final_stance": StanceType.CLARIFY,
                "final_advice": "최종적으로는 감정 추측보다 확인 가능한 행동을 기준으로 보세요. 답장 속도, 만남 제안에 대한 반응, 대화의 구체성을 함께 보고 짧게 확인 질문을 던지는 것이 가장 현실적입니다.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["최근 연락 패턴 적기", "짧은 확인 질문 보내기", "반응 기준 정하기"],
            },
            AgentId.EMPATH: {
                "final_stance": StanceType.PAUSE,
                "final_advice": "최종 입장은 먼저 마음을 안정시킨 뒤 확인하자는 쪽입니다. 상대 반응을 기다리는 동안 불안을 키우지 않도록 내 감정을 정리하고, 대화는 비난보다 솔직한 감정 공유로 시작하세요.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["불안한 지점 적기", "비난 없는 문장 만들기", "기다릴 시간 정하기"],
            },
            AgentId.ANALYST: {
                "final_stance": StanceType.MIXED,
                "final_advice": "최종적으로는 바로 단정하지 말고 최근 패턴을 근거로 판단해야 합니다. 답장이 느려진 기간, 말투 변화, 약속을 잡으려는 태도를 함께 비교한 뒤 확인 대화를 하는 편이 안전합니다.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["최근 변화 비교하기", "확인할 질문 정리하기", "단정 표현 피하기"],
            },
            AgentId.ACTOR: {
                "final_stance": StanceType.CLARIFY,
                "final_advice": "최종 의견은 작은 행동으로 상황을 움직여보자는 것입니다. 계속 기다리기보다 부담 없는 톤으로 근황을 묻고, 가능하면 짧은 만남이나 통화 제안을 해 반응을 확인하세요.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["오늘 보낼 문장 쓰기", "가벼운 만남 제안하기", "답변 후 다음 행동 정하기"],
            },
            AgentId.MEDIATOR: {
                "final_stance": StanceType.MIXED,
                "final_advice": "최종 입장은 내 감정과 상대의 사정을 함께 확인하자는 것입니다. 대화할 때는 왜 늦냐고 몰아붙이기보다, 요즘 바쁜지와 내가 느낀 불안을 같이 말해 균형을 잡으세요.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["상대 상황 묻기", "내 감정 한 문장으로 말하기", "서로 가능한 연락 방식 정하기"],
            },
            AgentId.FRIEND: {
                "final_stance": StanceType.CLARIFY,
                "final_advice": "최종 조언은 너무 무겁게 끌고 가지 말고 자연스럽게 확인해보자는 것입니다. 평소 말투로 요즘 좀 바쁜지 물어보고, 답을 들은 뒤 마음이 계속 불편하면 그때 진지하게 이야기하세요.",
                "changed_from_round_1": False,
                "change_reason": None,
                "action_items": ["평소 말투로 묻기", "상대 답변 여유 두기", "불편함이 남으면 다시 대화하기"],
            },
        }
        template = templates[agent_id]
        return AgentFinalPositionDraft(
            final_stance=template["final_stance"],
            final_advice=template["final_advice"],
            changed_from_round_1=template["changed_from_round_1"],
            change_reason=template["change_reason"],
            action_items=template["action_items"],
        )

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        return FinalPayload(
            situation="사용자는 상대의 반응을 해석하기 어려워 다음 행동을 고민하고 있습니다.",
            disagreements=["행동 시점을 바로 잡을지 조금 더 지켜볼지 의견 차이가 있습니다."],
            final_advice="상대의 마음을 단정하지 말고, 부담 없는 방식으로 확인하세요. 답을 기다리는 동안에는 내 감정 소모를 줄이는 기준도 함께 세우는 것이 좋습니다.",
            action_items=[
                ActionItem(
                    title="확인 질문 준비",
                    detail="상대가 부담을 느끼지 않도록 짧고 구체적인 질문을 한 문장으로 작성합니다.",
                    timing="immediate",
                ),
                ActionItem(
                    title="기다리는 기준 정하기",
                    detail="답변을 기다릴 기간과 이후 행동 기준을 미리 정해 감정 소모를 줄입니다.",
                    timing="short_term",
                ),
            ],
            caveats=[
                "상대의 의도는 현재 정보만으로 확정할 수 없습니다.",
                FINAL_CAVEAT_DISCLAIMER,
            ],
        )


class UpstageLLMClient:
    """Upstage adapter using the OpenAI-compatible chat completions interface."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.upstage.ai/v1",
        model: str = "solar-pro3",
        prompt_registry: PromptRegistry | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLM_PROVIDER=upstage") from exc

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._prompts = prompt_registry or PromptRegistry()

    async def _json_completion(
        self,
        task: str,
        output_schema: str,
        user: str,
        *,
        guidance: str = "",
        retry_feedback: str = "",
    ) -> dict:
        system = (
            "You are a backend JSON generator for a Korean relationship-consultation "
            "multi-agent workflow. Return exactly one JSON object and no markdown. "
            "Do not wrap the response in ```json fences. Use Korean text values. "
            "Never invent fields outside the requested schema. "
            "If a field has enum choices, use only one of the enum literals."
        )
        if guidance:
            system = f"{system}\n\nProject prompt guidance:\n{guidance}"
        prompt = (
            f"Task:\n{task}\n\n"
            f"Required JSON schema description:\n{output_schema}\n\n"
            f"Input context:\n{user}\n\n"
            "Return JSON only."
        )
        if retry_feedback:
            prompt = (
                f"{prompt}\n\n"
                "Previous output failed backend validation:\n"
                f"{retry_feedback}\n\n"
                "Retry by returning one corrected JSON object only. "
                "Keep enum literals, item counts, item lengths, and copied IDs exactly valid. "
                "Shorten every Korean text value if needed. Do not include raw newline characters "
                "inside JSON string values. Finish the closing braces."
            )
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    stream=False,
                    timeout=LLM_CALL_TIMEOUT_SECONDS,
                ),
                timeout=LLM_CALL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise LLMOutputError(
                code=ErrorCode.LLM_TIMEOUT,
                task=task,
                detail=f"LLM call exceeded {LLM_CALL_TIMEOUT_SECONDS:.0f}s timeout",
            ) from exc
        choice = response.choices[0]
        content = choice.message.content or "{}"
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason and finish_reason != "stop":
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=(
                    f"LLM finish_reason={finish_reason}. "
                    f"Response excerpt: {content[:320]!r}"
                ),
            )
        return _loads_json_object(content, task=task)

    async def _validated_json_completion(
        self,
        task: str,
        output_schema: str,
        user: str,
        *,
        guidance: str = "",
        validator: Callable[[dict], T],
    ) -> T:
        retry_feedback = ""
        max_attempts = _max_output_attempts()
        for attempt in range(1, max_attempts + 1):
            try:
                data = await self._json_completion(
                    task,
                    output_schema,
                    user,
                    guidance=guidance,
                    retry_feedback=retry_feedback,
                )
                return validator(data)
            except LLMOutputError as exc:
                retry_feedback = exc.detail
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=exc.code,
                        task=task,
                        detail=exc.detail,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(task, attempt=attempt, max_attempts=max_attempts, reason=exc.detail)
            except ValidationError as exc:
                retry_feedback = _validation_feedback(exc)
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=ErrorCode.SCHEMA_VIOLATION,
                        task=task,
                        detail=retry_feedback,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(
                    task,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    reason=retry_feedback,
                )
            except ValueError as exc:
                retry_feedback = str(exc)
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=ErrorCode.SCHEMA_VIOLATION,
                        task=task,
                        detail=retry_feedback,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(task, attempt=attempt, max_attempts=max_attempts, reason=retry_feedback)
        raise LLMOutputError(
            code=ErrorCode.UNKNOWN,
            task=task,
            detail="LLM output retry loop exited unexpectedly",
            retry_count=max_attempts - 1,
        )

    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        return await self._validated_json_completion(
            "Analyze the user's relationship concern for the supervisor analysis stage.",
            "\n".join(
                [
                    "{",
                    '  "relationship_state": "crush|dating|long_term|breakup_aftermath|ambiguous|other",',
                    '  "conflict_type": "communication_frequency|trust|future_alignment|emotional_distance|external_factor|ambiguous|other",',
                    '  "key_issues": ["1 to 5 short Korean strings"],',
                    '  "user_emotion": "anxious|confused|hurt|hopeful|angry|neutral",',
                    '  "debate_goal": "one Korean sentence"',
                    "}",
                ]
            ),
            user_question,
            guidance=self._prompts.supervisor_prompt("analysis"),
            validator=lambda data: _question_analysis_from_llm(data, consultation_id=consultation_id),
        )

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        return await self._validated_json_completion(
            f"Generate one round_1 independent opinion for agent_id={agent_id.value}.",
            "\n".join(
                [
                    "{",
                    '  "advice": "2 Korean paragraphs from your persona, each paragraph separated by \\n\\n, each paragraph 2-3 sentences, total 150-300 chars",',
                    '  "rationale": "1 to 2 Korean sentences explaining why",',
                    '  "stance": "proceed|pause|withdraw|clarify|mixed",',
                    '  "confidence": 0.0 to 1.0,',
                    '  "key_points": ["1 to 3 Korean strings, each max 60 chars"]',
                    "}",
                ]
            ),
            f"agent_id={agent_id.value}\nquestion={user_question}\nanalysis={analysis.model_dump_json()}",
            guidance=self._prompts.agent_round_prompt(agent_id, 1),
            validator=_agent_opinion_from_llm,
        )

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        return await self._validated_json_completion(
            "Summarize round_1 opinions into supervisor summary_1 payload.",
            "\n".join(
                [
                    "{",
                    '  "headline": "one Korean sentence, max 100 chars",',
                    '  "converging_points": ["0 to 5 Korean strings"],',
                    '  "diverging_points": ["0 to 5 Korean strings"],',
                    '  "open_questions": ["1 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "round_1_opinions": [
                        opinion.model_dump(mode="json") for opinion in round_1_opinions
                    ],
                }
            ),
            guidance=self._prompts.supervisor_prompt("summary_1"),
            validator=_summary1_payload_from_llm,
        )

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        round_1_opinions: list[AgentOpinion],
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        valid_id_to_agent: dict[str, AgentId] = {
            opinion.id: opinion.agent_id for opinion in round_1_opinions
        }
        return await self._validated_json_completion(
            f"Generate one round_2 rebuttal/complement for agent_id={agent_id.value}.",
            "\n".join(
                [
                    "{",
                    '  "targets": [{"target_message_id": "id copied from round_1_opinions", "target_agent_id": "agent_id matching that opinion", "agreement": "agree|partial|disagree|extend"}] (1 to 3 items, pick those most relevant to your persona),',
                    '  "statement": "Korean statement, 2 to 3 sentences engaging with the target opinion directly, max 300 chars",',
                    '  "rationale": "1 to 2 Korean sentences",',
                    '  "updated_position": "proceed|pause|withdraw|clarify|mixed or null",',
                    '  "new_evidence": ["0 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "agent_id": agent_id.value,
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "summary_1": summary_1.model_dump(mode="json"),
                    "round_1_opinions": [
                        opinion.model_dump(mode="json") for opinion in round_1_opinions
                    ],
                    "prior_round_2_rebuttals": [
                        rebuttal.model_dump(mode="json") for rebuttal in prior_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.agent_round_prompt(agent_id, 2),
            validator=lambda data: _validate_rebuttal_targets_against_opinions(
                _agent_rebuttal_from_llm(data),
                valid_id_to_agent=valid_id_to_agent,
            ),
        )

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        valid_message_ids = {rebuttal.id for rebuttal in round_2_rebuttals}
        return await self._validated_json_completion(
            "Classify round_2 into consensus, conflict, pending, and next action.",
            "\n".join(
                [
                    "{",
                    '  "consensus": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "conflict": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "pending": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "consensus_ratio": 0.0 to 1.0,',
                    '  "next_action": "proceed_to_round_3|skip_to_final"',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "summary_1": summary_1.model_dump(mode="json"),
                    "round_2_rebuttals": [
                        rebuttal.model_dump(mode="json") for rebuttal in round_2_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.supervisor_prompt("classify_2"),
            validator=lambda data: _validate_classify_supporting_ids(
                _classify2_payload_from_llm(data),
                valid_message_ids=valid_message_ids,
            ),
        )

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        return await self._validated_json_completion(
            f"Generate one round_3 final position for agent_id={agent_id.value}.",
            "\n".join(
                [
                    "{",
                    '  "final_stance": "proceed|pause|withdraw|clarify|mixed",',
                    '  "final_advice": "2 Korean paragraphs from your persona, each paragraph separated by \\n\\n, each paragraph 2-3 sentences, total 150-300 chars",',
                    '  "changed_from_round_1": true or false,',
                    '  "change_reason": "Korean reason, max 200 chars, or null",',
                    '  "action_items": ["0 to 3 Korean strings, each max 80 chars"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "agent_id": agent_id.value,
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "summary_1": summary_1.model_dump(mode="json"),
                    "classify_2": classify_2.model_dump(mode="json"),
                    "own_round_1_opinion": own_opinion.model_dump(mode="json")
                    if own_opinion
                    else None,
                    "own_round_2_rebuttal": own_rebuttal.model_dump(mode="json")
                    if own_rebuttal
                    else None,
                    "prior_round_3_positions": [
                        position.model_dump(mode="json") for position in prior_positions
                    ],
                }
            ),
            guidance=self._prompts.agent_round_prompt(agent_id, 3),
            validator=_agent_final_position_from_llm,
        )

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        return await self._validated_json_completion(
            "Create the supervisor final integrated consultation answer.",
            "\n".join(
                [
                    "{",
                    '  "situation": "Korean situation summary, max 600 chars",',
                    '  "disagreements": ["0 to 5 Korean strings"],',
                    '  "final_advice": "Korean final advice, max 800 chars",',
                    '  "action_items": [{"title": "max 50 chars", "detail": "max 200 chars", "timing": "immediate|short_term|long_term"}],',
                    '  "caveats": ["0 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json") if analysis else None,
                    "summary_1": summary_1.model_dump(mode="json") if summary_1 else None,
                    "classify_2": classify_2.model_dump(mode="json") if classify_2 else None,
                    "round_3_positions": [
                        position.model_dump(mode="json") for position in round_3_positions
                    ],
                    "round_2_rebuttals_fallback": [
                        rebuttal.model_dump(mode="json") for rebuttal in round_2_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.final_summary_prompt(),
            validator=_final_payload_from_llm,
        )


def build_llm_client_from_env() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockLLMClient()
    if provider == "upstage":
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY is required when LLM_PROVIDER=upstage")
        return UpstageLLMClient(
            api_key=api_key,
            base_url=os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
            model=os.getenv("UPSTAGE_MODEL", "solar-pro3"),
            prompt_registry=PromptRegistry(),
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


def _short_issue(user_question: str) -> str:
    stripped = " ".join(user_question.split())
    return stripped[:60] if stripped else "질문 핵심 파악 필요"


def _json_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _max_output_attempts() -> int:
    configured = os.getenv("LLM_OUTPUT_MAX_ATTEMPTS", "3")
    try:
        attempts = int(configured)
    except ValueError:
        attempts = 3
    return min(max(attempts, 1), 4)


def _log_llm_retry(task: str, *, attempt: int, max_attempts: int, reason: str) -> None:
    logger.warning(
        "retrying LLM output generation",
        extra={
            "task": task,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "reason_length": len(reason or ""),
            "reason": redact_for_log(reason, max_len=200),
        },
    )


def _validation_feedback(exc: ValidationError) -> str:
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
        details.append(f"{location}: {error.get('msg', 'validation failed')}")
    return "; ".join(details)[:1600]


def _question_analysis_from_llm(data: dict, *, consultation_id: str) -> QuestionAnalysis:
    repaired = dict(data)
    repaired["key_issues"] = _string_list(
        repaired.get("key_issues"),
        max_items=5,
        max_length=80,
        fallback=["관계 상황 확인 필요"],
    )
    repaired["debate_goal"] = _trim_text(
        repaired.get("debate_goal"),
        500,
        fallback="상황을 단정하지 않고 다음 행동을 정한다.",
    )
    return QuestionAnalysis(consultation_id=consultation_id, **repaired)


def _agent_opinion_from_llm(data: dict) -> AgentOpinionDraft:
    repaired = dict(data)
    repaired["advice"] = _trim_text(repaired.get("advice"), 700, fallback="상황을 더 확인하세요.")
    repaired["rationale"] = _trim_text(
        repaired.get("rationale"),
        300,
        fallback="현재 정보만으로는 단정하기 어렵습니다.",
    )
    repaired["key_points"] = _string_list(
        repaired.get("key_points"),
        max_items=3,
        max_length=60,
        fallback=["단정 금지"],
    )
    return AgentOpinionDraft(**repaired)


def _summary1_payload_from_llm(data: dict) -> Summary1Payload:
    repaired = dict(data)
    repaired["headline"] = _trim_text(
        repaired.get("headline"),
        100,
        fallback="답장 지연을 단정하지 말고 원인을 확인해야 한다.",
    )
    repaired["converging_points"] = _string_list(
        repaired.get("converging_points"),
        max_items=5,
        fallback=[],
    )
    repaired["diverging_points"] = _string_list(
        repaired.get("diverging_points"),
        max_items=5,
        fallback=[],
    )
    repaired["open_questions"] = _string_list(
        repaired.get("open_questions"),
        max_items=3,
        fallback=["상대방의 실제 상황은 무엇인가?"],
    )
    return Summary1Payload(**repaired)


def _agent_rebuttal_from_llm(data: dict) -> AgentRebuttalDraft:
    repaired = dict(data)
    repaired["statement"] = _trim_text(
        repaired.get("statement"),
        500,
        fallback="대상 의견을 보완해 상황 확인이 필요하다고 봅니다.",
    )
    repaired["rationale"] = _trim_text(
        repaired.get("rationale"),
        300,
        fallback="추측만으로는 관계 상태를 판단하기 어렵습니다.",
    )
    repaired["new_evidence"] = _string_list(
        repaired.get("new_evidence"),
        max_items=3,
        fallback=[],
    )
    return AgentRebuttalDraft(**repaired)


def _classify2_payload_from_llm(data: dict) -> Classify2Payload:
    repaired = dict(data)
    repaired["consensus"] = _classified_items(repaired.get("consensus"))
    repaired["conflict"] = _classified_items(repaired.get("conflict"))
    repaired["pending"] = _classified_items(repaired.get("pending"))
    return Classify2Payload(**repaired)


def _agent_final_position_from_llm(data: dict) -> AgentFinalPositionDraft:
    repaired = dict(data)
    repaired["final_advice"] = _trim_text(
        repaired.get("final_advice"),
        700,
        fallback="상황을 단정하지 말고 부드럽게 확인하세요.",
    )
    if repaired.get("change_reason") is not None:
        repaired["change_reason"] = _trim_text(repaired.get("change_reason"), 200)
    repaired["action_items"] = _string_list(
        repaired.get("action_items"),
        max_items=3,
        max_length=80,
        fallback=[],
    )
    return AgentFinalPositionDraft(**repaired)


FINAL_CAVEAT_DISCLAIMER = "이 답변은 전문 심리상담을 대체하지 않습니다."


def _ensure_disclaimer(caveats: list[str]) -> list[str]:
    if any(FINAL_CAVEAT_DISCLAIMER in caveat for caveat in caveats):
        return caveats
    if len(caveats) >= 3:
        # FinalPayload caps caveats at 3; replace the last so the disclaimer always survives.
        return [*caveats[:2], FINAL_CAVEAT_DISCLAIMER]
    return [*caveats, FINAL_CAVEAT_DISCLAIMER]


def _final_payload_from_llm(data: dict) -> FinalPayload:
    repaired = dict(data)
    repaired["situation"] = _trim_text(
        repaired.get("situation"),
        600,
        fallback="사용자는 상대방의 답장 지연을 관계 변화로 봐야 하는지 고민하고 있습니다.",
    )
    repaired["disagreements"] = _string_list(
        repaired.get("disagreements"),
        max_items=5,
        fallback=[],
    )
    repaired["final_advice"] = _trim_text(
        repaired.get("final_advice"),
        800,
        fallback="답장 속도만으로 단정하지 말고 상대방의 상황과 메시지 패턴을 함께 확인하세요.",
    )
    repaired["caveats"] = _ensure_disclaimer(
        _string_list(repaired.get("caveats"), max_items=3, fallback=[])
    )
    action_items = repaired.get("action_items")
    normalized_action_items = []
    if isinstance(action_items, list):
        normalized_action_items = [
            {
                **item,
                "title": _trim_text(item.get("title"), 50, fallback="상황 확인"),
                "detail": _trim_text(
                    item.get("detail"),
                    200,
                    fallback="상대방의 현재 상황을 부드럽게 확인하세요.",
                ),
            }
            for item in action_items[:5]
            if isinstance(item, dict)
        ]
    if not normalized_action_items:
        normalized_action_items = [
            {
                "title": "상황 확인",
                "detail": "상대방의 현재 상황을 부드럽게 확인하세요.",
                "timing": "immediate",
            }
        ]
    repaired["action_items"] = normalized_action_items
    return FinalPayload(**repaired)


def _validate_rebuttal_targets_against_opinions(
    draft: AgentRebuttalDraft,
    *,
    valid_id_to_agent: dict[str, AgentId],
) -> AgentRebuttalDraft:
    if not valid_id_to_agent:
        raise ValueError(
            "round_1_opinions is empty; round_2 rebuttal cannot reference any target"
        )
    valid_ids_sorted = sorted(valid_id_to_agent.keys())
    for target in draft.targets:
        expected_agent_id = valid_id_to_agent.get(target.target_message_id)
        if expected_agent_id is None:
            raise ValueError(
                "targets[*].target_message_id must reference an id from round_1_opinions. "
                f"received={target.target_message_id}; valid={valid_ids_sorted}"
            )
        if expected_agent_id != target.target_agent_id:
            raise ValueError(
                "targets[*].target_agent_id does not match the round_1_opinion's agent_id. "
                f"target_message_id={target.target_message_id} "
                f"expected={expected_agent_id.value} received={target.target_agent_id.value}"
            )
    return draft


def _validate_classify_supporting_ids(
    payload: Classify2Payload,
    *,
    valid_message_ids: set[str],
) -> Classify2Payload:
    invalid_ids = sorted(
        {
            message_id
            for item in [*payload.consensus, *payload.conflict, *payload.pending]
            for message_id in item.supporting_message_ids
            if message_id not in valid_message_ids
        }
    )
    if invalid_ids:
        raise ValueError(
            "supporting_message_ids must be copied from input round_2_rebuttals ids. "
            f"invalid={invalid_ids}; valid={sorted(valid_message_ids)}"
        )
    return payload


def _classified_items(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                **item,
                "topic": _trim_text(item.get("topic"), 100, fallback="미도출"),
                "supporting_message_ids": _string_list(
                    item.get("supporting_message_ids"),
                    max_items=20,
                    fallback=[],
                ),
            }
        )
    return items


def _string_list(
    value: object,
    *,
    max_items: int,
    fallback: list[str],
    max_length: int | None = None,
) -> list[str]:
    if not isinstance(value, list):
        value = fallback
    strings = [item for item in value if isinstance(item, str) and item.strip()]
    strings = strings[:max_items]
    if max_length is not None:
        strings = [_trim_text(item, max_length) for item in strings]
    return strings


def _trim_text(value: object, max_length: int, *, fallback: str = "") -> str:
    text = value if isinstance(value, str) else fallback
    text = " ".join(text.split())
    if not text:
        text = fallback
    return text[:max_length]


def _loads_json_object(content: str, *, task: str = "unknown") -> dict:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as first_exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            snippet = stripped[:320]
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=(
                    f"{first_exc.msg} at char {first_exc.pos}. "
                    f"Response excerpt: {snippet!r}"
                ),
            ) from first_exc
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            snippet_start = max(0, exc.pos - 160)
            snippet_end = min(len(stripped), exc.pos + 160)
            snippet = stripped[snippet_start:snippet_end]
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=f"{exc.msg} at char {exc.pos}. Response excerpt: {snippet!r}",
            ) from exc

    if not isinstance(parsed, dict):
        raise LLMOutputError(
            code=ErrorCode.JSON_PARSE_FAILED,
            task=task,
            detail="LLM response must be a JSON object",
        )
    return parsed
