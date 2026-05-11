from __future__ import annotations

import json
import asyncio
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
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
    QuestionAnalysis,
    StanceType,
    SupervisorNote,
    TargetReference,
)
from app.services.llm_client import (
    AgentOpinionDraft,
    AgentRebuttalDraft,
    LLMOutputError,
    MockLLMClient,
    UpstageLLMClient,
    _loads_json_object,
)
from app.services.prompts import PromptRegistry


def test_health() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_local_test_origin() -> None:
    with TestClient(create_app()) as client:
        response = client.options(
            "/consultations",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_create_and_read_completed_consultation() -> None:
    with TestClient(create_app()) as client:
        consultation_id = str(uuid4())
        response = client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "상대방 답장이 느려서 마음이 식은 건지 고민돼.",
                "language": "ko-KR",
            },
        )

        assert response.status_code == 202
        assert response.json() == {"consultation_id": consultation_id, "status": "pending"}

        body = wait_for_completed(client, consultation_id)

    assert body["status"] == "completed"
    assert body["analysis"]["consultation_id"] == consultation_id
    assert len(body["rounds"]) == 3
    assert len(body["rounds"][0]["messages"]) == 6
    assert len(body["rounds"][1]["messages"]) == 6
    assert len(body["rounds"][2]["messages"]) == 6
    round_2_statements = [message["statement"] for message in body["rounds"][1]["messages"]]
    assert len(set(round_2_statements)) == len(round_2_statements)
    assert all(len(statement) >= 80 for statement in round_2_statements)
    for message in body["rounds"][1]["messages"]:
        target_agent_id = AgentId(message["targets"][0]["target_agent_id"])
        assert AGENT_NAMES[target_agent_id] in message["statement"]
    round_3_advices = [message["final_advice"] for message in body["rounds"][2]["messages"]]
    assert len(set(round_3_advices)) == len(round_3_advices)
    assert all(len(advice) >= 70 for advice in round_3_advices)
    assert body["final"]["final_advice"]


def test_duplicate_post_is_idempotent() -> None:
    with TestClient(create_app()) as client:
        consultation_id = str(uuid4())
        payload = {
            "consultation_id": consultation_id,
            "user_question": "첫 데이트 이후 연락 빈도가 줄었어.",
            "language": "ko-KR",
        }

        first = client.post("/consultations", json=payload)
        second = client.post("/consultations", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["consultation_id"] == consultation_id


def test_request_schema_rejects_non_uuid_v4_id() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/consultations",
            json={
                "consultation_id": "not-a-uuid",
                "user_question": "상담이 필요해.",
                "language": "ko-KR",
            },
        )

    assert response.status_code == 422


def test_llm_json_loader_accepts_plain_and_fenced_json() -> None:
    assert _loads_json_object('{"advice": "확인하세요"}') == {"advice": "확인하세요"}
    assert _loads_json_object('```json\n{"advice": "확인하세요"}\n```') == {
        "advice": "확인하세요"
    }


def test_llm_json_loader_error_includes_task_and_excerpt() -> None:
    try:
        _loads_json_object('{"advice" "missing colon"}', task="agent-opinion-test")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected ValueError")

    assert "agent-opinion-test" in message
    assert "Response excerpt" in message


def test_upstage_client_retries_schema_validation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_OUTPUT_MAX_ATTEMPTS", "2")

    class RetrySchemaClient(UpstageLLMClient):
        def __init__(self) -> None:
            self.calls = 0
            self.feedback: list[str] = []
            self._prompts = PromptRegistry()

        async def _json_completion(self, *args, retry_feedback: str = "", **kwargs):
            self.calls += 1
            self.feedback.append(retry_feedback)
            if self.calls == 1:
                return {
                    "advice": "advice",
                    "rationale": "rationale",
                    "stance": "not-a-valid-stance",
                    "confidence": 0.8,
                    "key_points": ["short"],
                }
            return {
                "advice": "advice",
                "rationale": "rationale",
                "stance": "clarify",
                "confidence": 0.8,
                "key_points": ["short"],
            }

    analysis = QuestionAnalysis(
        consultation_id=str(uuid4()),
        relationship_state="ambiguous",
        conflict_type="ambiguous",
        key_issues=["issue"],
        user_emotion="neutral",
        debate_goal="goal",
    )
    client = RetrySchemaClient()

    draft = asyncio.run(client.create_agent_opinion(AgentId.REALIST, "question", analysis))

    assert isinstance(draft, AgentOpinionDraft)
    assert client.calls == 2
    assert "stance" in client.feedback[1]


def test_upstage_client_normalizes_summary_list_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_OUTPUT_MAX_ATTEMPTS", "2")

    class OverflowSummaryClient(UpstageLLMClient):
        def __init__(self) -> None:
            self.calls = 0
            self._prompts = PromptRegistry()

        async def _json_completion(self, *args, **kwargs):
            self.calls += 1
            return {
                "headline": "headline",
                "converging_points": [],
                "diverging_points": [f"point-{index}" for index in range(6)],
                "open_questions": ["question"],
            }

    analysis = QuestionAnalysis(
        consultation_id=str(uuid4()),
        relationship_state="ambiguous",
        conflict_type="ambiguous",
        key_issues=["issue"],
        user_emotion="neutral",
        debate_goal="goal",
    )
    client = OverflowSummaryClient()

    payload = asyncio.run(client.summarize_round_1("question", analysis, []))

    assert len(payload.diverging_points) == 5
    assert client.calls == 1


def test_upstage_client_retries_invalid_classify_supporting_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_OUTPUT_MAX_ATTEMPTS", "2")

    class RetryClassifyClient(UpstageLLMClient):
        def __init__(self, valid_id: str) -> None:
            self.valid_id = valid_id
            self.calls = 0
            self.feedback: list[str] = []
            self._prompts = PromptRegistry()

        async def _json_completion(self, *args, retry_feedback: str = "", **kwargs):
            self.calls += 1
            self.feedback.append(retry_feedback)
            supporting_id = "not-from-input" if self.calls == 1 else self.valid_id
            return {
                "consensus": [
                    {"topic": "topic", "supporting_message_ids": [supporting_id]},
                ],
                "conflict": [],
                "pending": [],
                "consensus_ratio": 1.0,
                "next_action": "skip_to_final",
            }

    rebuttal = _sample_rebuttal()
    summary = SupervisorNote(
        consultation_id=rebuttal.consultation_id,
        mode="summary_1",
        payload={"headline": "summary"},
    )
    client = RetryClassifyClient(rebuttal.id)

    payload = asyncio.run(client.classify_round_2(summary, [rebuttal]))

    assert payload.consensus[0].supporting_message_ids == [rebuttal.id]
    assert client.calls == 2
    assert "supporting_message_ids" in client.feedback[1]


def test_llm_output_error_maps_to_public_error_code() -> None:
    class FailingOutputLLMClient(MockLLMClient):
        async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task="analysis",
                detail="internal raw response excerpt",
                retry_count=1,
            )

    with TestClient(create_app(llm_client=FailingOutputLLMClient())) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "Force LLM output failure.",
                "language": "ko-KR",
            },
        )
        body = wait_for_status(client, consultation_id, {"failed"})

        with client.stream("GET", f"/consultations/{consultation_id}/events") as response:
            assert response.status_code == 200
            text = "".join(response.iter_text())

    assert body["errors"][0]["code"] == "JSON_PARSE_FAILED"
    event = _sse_event_by_type(text, "error_occurred")
    assert event["payload"]["error"] == {
        "code": "JSON_PARSE_FAILED",
        "user_message_key": "error.json_parse_failed",
        "affected_agent": None,
    }
    assert "internal raw response excerpt" not in json.dumps(event, ensure_ascii=False)


def test_completed_sse_history_contains_workflow_events() -> None:
    with TestClient(create_app()) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "친구처럼 지내는 상대에게 고백해도 될지 모르겠어.",
                "language": "ko-KR",
            },
        )
        wait_for_completed(client, consultation_id)

        with client.stream("GET", f"/consultations/{consultation_id}/events") as response:
            assert response.status_code == 200
            text = "".join(response.iter_text())

    assert "event: status_changed" in text
    assert "event: analysis_completed" in text
    assert "event: agent_message_added" in text
    assert "event: supervisor_note_added" in text
    assert "event: completed" in text


def test_consensus_skip_to_final_omits_round_3() -> None:
    class ConsensusMockLLMClient(MockLLMClient):
        async def classify_round_2(self, summary_1, round_2_rebuttals) -> Classify2Payload:
            rebuttal_ids = [item.id for item in round_2_rebuttals]
            return Classify2Payload(
                consensus=[
                    ClassifiedItem(
                        topic="답장 텀만으로 관심을 단정하지 않는다",
                        supporting_message_ids=rebuttal_ids,
                    )
                ],
                conflict=[],
                pending=[],
                consensus_ratio=1.0,
                next_action="skip_to_final",
            )

    with TestClient(create_app(llm_client=ConsensusMockLLMClient())) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "대부분 의견이 같으면 3라운드를 생략하는지 확인해줘.",
                "language": "ko-KR",
            },
        )

        body = wait_for_terminal(client, consultation_id)

    assert body["status"] == "terminated"
    assert body["termination"]["reason"] == "consensus_reached"
    assert [item["round"] for item in body["rounds"]] == ["round_1", "round_2"]


def test_prompt_registry_loads_selected_prompt_files() -> None:
    registry = PromptRegistry()

    assert "중립적 조정자" in registry.supervisor_prompt("analysis")
    assert "현실주의자" in registry.agent_round_prompt(AgentId.REALIST, 1)
    assert "최종 통합" in registry.final_summary_prompt()


def test_rich_context_is_passed_to_llm_stages() -> None:
    class RecordingLLMClient(MockLLMClient):
        def __init__(self) -> None:
            self.summary_opinion_advice: list[str] = []
            self.rebuttal_target_advice: list[str] = []
            self.classify_statements: list[str] = []
            self.round_3_context_seen = False
            self.final_context_seen = False

        async def summarize_round_1(self, user_question, analysis, round_1_opinions):
            self.summary_opinion_advice = [item.advice for item in round_1_opinions]
            return await super().summarize_round_1(user_question, analysis, round_1_opinions)

        async def create_agent_rebuttal(
            self,
            agent_id,
            user_question,
            analysis,
            summary_1,
            round_1_opinions,
            prior_rebuttals,
        ):
            target_opinion = next(
                (opinion for opinion in round_1_opinions if opinion.agent_id != agent_id),
                round_1_opinions[0],
            )
            self.rebuttal_target_advice.append(target_opinion.advice)
            return await super().create_agent_rebuttal(
                agent_id,
                user_question,
                analysis,
                summary_1,
                round_1_opinions,
                prior_rebuttals,
            )

        async def classify_round_2(self, summary_1, round_2_rebuttals):
            self.classify_statements = [item.statement for item in round_2_rebuttals]
            return await super().classify_round_2(summary_1, round_2_rebuttals)

        async def create_agent_final_position(
            self,
            agent_id,
            user_question,
            analysis,
            summary_1,
            classify_2,
            own_opinion,
            own_rebuttal,
            prior_positions,
        ):
            self.round_3_context_seen = own_opinion is not None and own_rebuttal is not None
            return await super().create_agent_final_position(
                agent_id,
                user_question,
                analysis,
                summary_1,
                classify_2,
                own_opinion,
                own_rebuttal,
                prior_positions,
            )

        async def create_final_summary(
            self,
            user_question,
            analysis,
            summary_1,
            classify_2,
            round_3_positions,
            round_2_rebuttals,
        ):
            self.final_context_seen = (
                analysis is not None
                and summary_1 is not None
                and classify_2 is not None
                and bool(round_3_positions)
            )
            return await super().create_final_summary(
                user_question,
                analysis,
                summary_1,
                classify_2,
                round_3_positions,
                round_2_rebuttals,
            )

    llm = RecordingLLMClient()
    with TestClient(create_app(llm_client=llm)) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "Need context-rich prompts for this consultation.",
                "language": "ko-KR",
            },
        )
        wait_for_completed(client, consultation_id)

    assert llm.summary_opinion_advice
    assert llm.rebuttal_target_advice
    assert llm.classify_statements
    assert llm.round_3_context_seen
    assert llm.final_context_seen


def test_inconsistent_skip_to_final_is_normalized_to_round_3() -> None:
    class InconsistentClassifyLLMClient(MockLLMClient):
        async def classify_round_2(self, summary_1, round_2_rebuttals) -> Classify2Payload:
            return Classify2Payload(
                consensus=[],
                conflict=[],
                pending=[],
                consensus_ratio=0.0,
                next_action="skip_to_final",
            )

    with TestClient(create_app(llm_client=InconsistentClassifyLLMClient())) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "Do not skip without consensus evidence.",
                "language": "ko-KR",
            },
        )
        body = wait_for_completed(client, consultation_id)

    assert body["termination"] is None
    assert [item["round"] for item in body["rounds"]] == ["round_1", "round_2", "round_3"]
    classify_payload = body["rounds"][1]["supervisor_note"]["payload"]
    assert classify_payload["next_action"] == "proceed_to_round_3"
    assert classify_payload["pending"][0]["topic"] == "미도출"


def test_schema_item_length_and_change_reason_contracts() -> None:
    with pytest.raises(ValidationError):
        QuestionAnalysis(
            consultation_id=str(uuid4()),
            relationship_state="ambiguous",
            conflict_type="ambiguous",
            key_issues=["x" * 81],
            user_emotion="neutral",
            debate_goal="test",
        )

    with pytest.raises(ValidationError):
        AgentOpinion(
            consultation_id=str(uuid4()),
            agent_id=AgentId.REALIST,
            agent_name="현실주의자",
            advice="advice",
            rationale="rationale",
            stance=StanceType.CLARIFY,
            confidence=0.5,
            key_points=["x" * 61],
        )

    with pytest.raises(ValidationError):
        AgentFinalPosition(
            consultation_id=str(uuid4()),
            agent_id=AgentId.REALIST,
            agent_name="현실주의자",
            final_stance=StanceType.CLARIFY,
            final_advice="advice",
            changed_from_round_1=True,
            change_reason=None,
            action_items=["do it"],
        )


def test_invalid_rebuttal_target_fails_workflow() -> None:
    class InvalidTargetLLMClient(MockLLMClient):
        async def create_agent_rebuttal(
            self,
            agent_id,
            user_question,
            analysis,
            summary_1,
            round_1_opinions,
            prior_rebuttals,
        ):
            return AgentRebuttalDraft(
                targets=[
                    TargetReference(
                        target_message_id=str(uuid4()),
                        target_agent_id=AgentId.REALIST,
                        agreement=AgreementType.PARTIAL,
                    )
                ],
                statement="invalid target reference",
                rationale="target id is not from round one",
            )

    with TestClient(create_app(llm_client=InvalidTargetLLMClient())) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "Invalid target should fail.",
                "language": "ko-KR",
            },
        )
        body = wait_for_status(client, consultation_id, {"failed"})

    assert body["status"] == "failed"
    assert body["errors"][0]["user_message_key"] == "error.schema_violation"


def test_error_sse_uses_public_error_contract() -> None:
    class FailingAnalysisLLMClient(MockLLMClient):
        async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
            raise RuntimeError("internal secret detail")

    with TestClient(create_app(llm_client=FailingAnalysisLLMClient())) as client:
        consultation_id = str(uuid4())
        client.post(
            "/consultations",
            json={
                "consultation_id": consultation_id,
                "user_question": "Force failure.",
                "language": "ko-KR",
            },
        )
        wait_for_status(client, consultation_id, {"failed"})

        with client.stream("GET", f"/consultations/{consultation_id}/events") as response:
            assert response.status_code == 200
            text = "".join(response.iter_text())

    event = _sse_event_by_type(text, "error_occurred")
    error = event["payload"]["error"]
    assert error == {
        "code": "UNKNOWN",
        "user_message_key": "error.unknown",
        "affected_agent": None,
    }
    assert "internal secret detail" not in json.dumps(event, ensure_ascii=False)


def _sample_rebuttal() -> AgentRebuttal:
    return AgentRebuttal(
        consultation_id=str(uuid4()),
        agent_id=AgentId.REALIST,
        agent_name="realist",
        targets=[
            TargetReference(
                target_message_id=str(uuid4()),
                target_agent_id=AgentId.REALIST,
                agreement=AgreementType.PARTIAL,
            )
        ],
        statement="statement",
        rationale="rationale",
    )


def wait_for_completed(client: TestClient, consultation_id: str) -> dict:
    body = wait_for_terminal(client, consultation_id)
    if body["status"] != "completed":
        raise AssertionError(body)
    return body


def wait_for_terminal(client: TestClient, consultation_id: str) -> dict:
    return wait_for_status(client, consultation_id, {"completed", "terminated"})


def wait_for_status(client: TestClient, consultation_id: str, statuses: set[str]) -> dict:
    for _ in range(100):
        response = client.get(f"/consultations/{consultation_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in statuses:
            return body
        if body["status"] == "failed" and "failed" not in statuses:
            raise AssertionError(body)
        time.sleep(0.02)
    raise AssertionError(f"consultation did not reach {statuses}")


def _sse_event_by_type(text: str, event_type: str) -> dict:
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        event_line = next((line for line in lines if line.startswith("event: ")), "")
        if event_line.removeprefix("event: ") != event_type:
            continue
        data_line = next(line for line in lines if line.startswith("data: "))
        return json.loads(data_line.removeprefix("data: "))
    raise AssertionError(f"SSE event not found: {event_type}")
