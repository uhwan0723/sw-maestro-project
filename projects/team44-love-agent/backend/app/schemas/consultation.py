from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = "1.0.0"
LANGUAGE = "ko-KR"


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_message_id() -> str:
    return str(uuid4())


def _validate_items_max_length(values: list[str], *, max_length: int, field_name: str) -> list[str]:
    too_long = [index for index, value in enumerate(values) if len(value) > max_length]
    if too_long:
        raise ValueError(f"{field_name} items must be at most {max_length} characters")
    return values


class AgentId(str, Enum):
    REALIST = "realist"
    EMPATH = "empath"
    ANALYST = "analyst"
    ACTOR = "actor"
    MEDIATOR = "mediator"
    FRIEND = "friend"
    SUPERVISOR = "supervisor"


AGENT_NAMES: dict[AgentId, str] = {
    AgentId.REALIST: "현실주의자",
    AgentId.EMPATH: "공감형 감성론자",
    AgentId.ANALYST: "신중한 분석가",
    AgentId.ACTOR: "행동파 조언자",
    AgentId.MEDIATOR: "균형형 중재자",
    AgentId.FRIEND: "친구형 상담자",
    AgentId.SUPERVISOR: "슈퍼바이저",
}

ROUND_1_AGENT_ORDER = [
    AgentId.REALIST,
    AgentId.EMPATH,
    AgentId.ANALYST,
    AgentId.ACTOR,
    AgentId.MEDIATOR,
    AgentId.FRIEND,
]

SEQUENTIAL_AGENT_ORDER = [
    AgentId.REALIST,
    AgentId.ANALYST,
    AgentId.MEDIATOR,
    AgentId.EMPATH,
    AgentId.ACTOR,
    AgentId.FRIEND,
]


class StanceType(str, Enum):
    PROCEED = "proceed"
    PAUSE = "pause"
    WITHDRAW = "withdraw"
    CLARIFY = "clarify"
    MIXED = "mixed"


class AgreementType(str, Enum):
    AGREE = "agree"
    PARTIAL = "partial"
    DISAGREE = "disagree"
    EXTEND = "extend"


class RoundType(str, Enum):
    ANALYSIS = "analysis"
    ROUND_1 = "round_1"
    SUMMARY_1 = "summary_1"
    ROUND_2 = "round_2"
    CLASSIFY_2 = "classify_2"
    ROUND_3 = "round_3"
    FINAL = "final"


class ConsultationStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    ROUND_1_RUNNING = "round_1_running"
    SUMMARY_1_RUNNING = "summary_1_running"
    ROUND_2_RUNNING = "round_2_running"
    CLASSIFY_2_RUNNING = "classify_2_running"
    ROUND_3_RUNNING = "round_3_running"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    FAILED = "failed"


class TerminationReason(str, Enum):
    NORMAL = "normal"
    CONSENSUS_REACHED = "consensus_reached"
    REPETITION_DETECTED = "repetition_detected"
    ROUND_LIMIT_EXCEEDED = "round_limit_exceeded"
    PERSONA_BREAKDOWN = "persona_breakdown"
    SAFETY_FILTER = "safety_filter"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"


class ErrorCode(str, Enum):
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    JSON_PARSE_FAILED = "JSON_PARSE_FAILED"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    PERSONA_DRIFT = "PERSONA_DRIFT"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    WORKFLOW_TIMEOUT = "WORKFLOW_TIMEOUT"
    UNKNOWN = "UNKNOWN"


class SchemaModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False)


class ClientMeta(SchemaModel):
    user_agent: str | None = None
    submitted_at: str | None = None


class UserConsultationRequest(SchemaModel):
    consultation_id: str
    user_question: str = Field(min_length=1, max_length=4000)
    language: Literal["ko-KR"] = LANGUAGE
    client_meta: ClientMeta | None = None

    @field_validator("consultation_id")
    @classmethod
    def validate_consultation_id(cls, value: str) -> str:
        try:
            parsed = UUID(value)
        except ValueError as exc:
            raise ValueError("consultation_id must be a UUID string") from exc
        if parsed.version != 4:
            raise ValueError("consultation_id must be a UUID v4 string")
        return value


class ConsultationStartResponse(SchemaModel):
    consultation_id: str
    status: ConsultationStatus


class TimestampedMessage(SchemaModel):
    id: str = Field(default_factory=new_message_id)
    created_at: str = Field(default_factory=utc_now_iso)
    language: Literal["ko-KR"] = LANGUAGE
    meta: dict[str, Any] = Field(default_factory=dict)


class QuestionAnalysis(TimestampedMessage):
    consultation_id: str
    relationship_state: Literal[
        "crush", "dating", "long_term", "breakup_aftermath", "ambiguous", "other"
    ]
    conflict_type: Literal[
        "communication_frequency",
        "trust",
        "future_alignment",
        "emotional_distance",
        "external_factor",
        "ambiguous",
        "other",
    ]
    key_issues: list[str] = Field(min_length=1, max_length=5)
    user_emotion: Literal["anxious", "confused", "hurt", "hopeful", "angry", "neutral"]
    debate_goal: str = Field(min_length=1)

    @field_validator("key_issues")
    @classmethod
    def validate_key_issue_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=80, field_name="key_issues")


class AgentOpinion(TimestampedMessage):
    consultation_id: str
    round: Literal["round_1"] = "round_1"
    agent_id: AgentId
    agent_name: str
    advice: str = Field(min_length=1, max_length=700)
    rationale: str = Field(min_length=1, max_length=300)
    stance: StanceType
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str] = Field(min_length=1, max_length=3)

    @field_validator("key_points")
    @classmethod
    def validate_key_point_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=60, field_name="key_points")


class TargetReference(SchemaModel):
    target_message_id: str
    target_agent_id: AgentId
    agreement: AgreementType


class AgentRebuttal(TimestampedMessage):
    consultation_id: str
    round: Literal["round_2"] = "round_2"
    agent_id: AgentId
    agent_name: str
    targets: list[TargetReference] = Field(min_length=1, max_length=3)
    statement: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=300)
    updated_position: StanceType | None = None
    new_evidence: list[str] = Field(default_factory=list, max_length=3)


class AgentFinalPosition(TimestampedMessage):
    consultation_id: str
    round: Literal["round_3"] = "round_3"
    agent_id: AgentId
    agent_name: str
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
    def validate_change_reason_required(self) -> "AgentFinalPosition":
        if self.changed_from_round_1 and not self.change_reason:
            raise ValueError("change_reason is required when changed_from_round_1 is true")
        return self


class Summary1Payload(SchemaModel):
    headline: str = Field(min_length=1, max_length=100)
    converging_points: list[str] = Field(default_factory=list, max_length=5)
    diverging_points: list[str] = Field(default_factory=list, max_length=5)
    open_questions: list[str] = Field(min_length=1, max_length=3)


class ClassifiedItem(SchemaModel):
    topic: str = Field(min_length=1, max_length=100)
    supporting_message_ids: list[str] = Field(default_factory=list)


class Classify2Payload(SchemaModel):
    consensus: list[ClassifiedItem] = Field(default_factory=list)
    conflict: list[ClassifiedItem] = Field(default_factory=list)
    pending: list[ClassifiedItem] = Field(default_factory=list)
    consensus_ratio: float = Field(ge=0.0, le=1.0)
    next_action: Literal["proceed_to_round_3", "skip_to_final"]


class ActionItem(SchemaModel):
    title: str = Field(min_length=1, max_length=50)
    detail: str = Field(min_length=1, max_length=200)
    timing: Literal["immediate", "short_term", "long_term"]


class FinalPayload(SchemaModel):
    situation: str = Field(min_length=1, max_length=600)
    disagreements: list[str] = Field(default_factory=list, max_length=5)
    final_advice: str = Field(min_length=1, max_length=800)
    action_items: list[ActionItem] = Field(min_length=1, max_length=5)
    caveats: list[str] = Field(default_factory=list, max_length=3)


class SupervisorNote(TimestampedMessage):
    consultation_id: str
    mode: Literal["analysis", "summary_1", "classify_2", "final"]
    payload: dict[str, Any]


class ErrorEvent(TimestampedMessage):
    code: ErrorCode
    where: str
    detail: str
    retry_count: int = 0
    fatal: bool = False


class SkippedAgent(SchemaModel):
    agent_id: AgentId
    round: RoundType
    reason: ErrorCode
    occurred_at: str


class Termination(SchemaModel):
    reason: TerminationReason
    occurred_at: str
    notes: str | None = None


class PublicError(SchemaModel):
    code: ErrorCode
    user_message_key: str
    affected_agent: AgentId | None = None


class PublicTermination(SchemaModel):
    reason: TerminationReason
    user_message_key: str


class PublicRound(SchemaModel):
    round: RoundType
    started_at: str
    completed_at: str
    messages: list[AgentOpinion | AgentRebuttal | AgentFinalPosition]
    supervisor_note: SupervisorNote | None = None


class PublicFinalSummary(SchemaModel):
    situation: str
    disagreements: list[str]
    final_advice: str
    action_items: list[ActionItem]
    caveats: list[str]
    contributing_agents: list[AgentId]


class ConsultationResponse(SchemaModel):
    consultation_id: str
    status: ConsultationStatus
    started_at: str
    completed_at: str | None = None
    user_question: str
    language: Literal["ko-KR"] = LANGUAGE
    analysis: QuestionAnalysis | None = None
    rounds: list[PublicRound] = Field(default_factory=list)
    final: PublicFinalSummary | None = None
    termination: PublicTermination | None = None
    errors: list[PublicError] = Field(default_factory=list)


class ConsultationState(SchemaModel):
    consultation_id: str
    started_at: str
    updated_at: str
    status: ConsultationStatus
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    user_question: str
    language: Literal["ko-KR"] = LANGUAGE
    analysis: QuestionAnalysis | None = None
    summary_1: SupervisorNote | None = None
    classify_2: SupervisorNote | None = None
    final_summary: SupervisorNote | None = None
    round_1_opinions: list[AgentOpinion] = Field(default_factory=list)
    round_2_rebuttals: list[AgentRebuttal] = Field(default_factory=list)
    round_3_positions: list[AgentFinalPosition] = Field(default_factory=list)
    errors: list[ErrorEvent] = Field(default_factory=list)
    skipped_agents: list[SkippedAgent] = Field(default_factory=list)
    termination: Termination | None = None
    completed_at: str | None = None
