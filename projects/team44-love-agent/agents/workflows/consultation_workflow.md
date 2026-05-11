# Consultation Workflow

사용자 질문 입력부터 최종 상담 결과 반환까지 이어지는 멀티 Agent 실행 골격입니다. 이 문서는 김민우 담당인 **실행 순서, 라운드 처리 흐름, 데이터 저장 구조, 백엔드/API 연결 구조**를 구현 전 검토할 수 있도록 정리합니다. 현재 확정 구현 기준은 **FastAPI 단일 서버 + LangGraph + in-memory state + SSE**입니다.

## 1. 담당과 기준 문서

| 항목 | 내용 |
| --- | --- |
| 주 담당 | 김민우 — 워크플로우/백엔드 골격 |
| 프로토콜 검토 | 신현성 — 메시지 스키마, 라운드 입출력, 슈퍼바이저 규칙 |
| 프론트 연동 검토 | 김준서, 박준혁 — 상태 표시, 사용자 문구 키, 토론 로그 표시 |
| 프롬프트 연동 검토 | 임지빈 — Agent/Supervisor 출력 JSON 형식 |

기준 문서:

- [`message_schema.md`](message_schema.md): 모든 입력/출력/상태/응답/스트리밍 이벤트의 JSON 계약
- [`supervisor_protocol.md`](supervisor_protocol.md): LangGraph 토폴로지, conditional edge, 실패/재시도/스킵 규칙
- [`../../backend/README.md`](../../backend/README.md): 백엔드 API와 실행 연결 책임
- [`../../docs/team44-love-agent/03_features_workflow/features_and_workflow.md`](../../docs/team44-love-agent/03_features_workflow/features_and_workflow.md): 사용자/시스템 관점 흐름
- [`../../docs/team44-love-agent/03_features_workflow/user_messages.md`](../../docs/team44-love-agent/03_features_workflow/user_messages.md): 사용자 노출 문구 key 사전

## 2. 구현 범위

이번 문서는 실제 코드가 아니라 **개발 전에 합의할 워크플로우 spec + 의사코드**입니다. 다만 다음 구현 단계에서 바로 `backend/app` 코드로 옮길 수 있도록 FastAPI/LangGraph 기준으로 작성합니다.

### In scope

- 상담 요청 1건을 `ConsultationState`로 초기화하는 흐름
- `POST /consultations`, `GET /consultations/{consultation_id}`, `GET /consultations/{consultation_id}/events` API 연결 방향
- `consultation_id`별 in-memory state와 SSE event queue 분리
- 슈퍼바이저 4회 호출 지점
- 1라운드 병렬, 2·3라운드 순차 호출 구조
- conditional edge 조건
- JSON 파싱/스키마 검증/재시도/스킵/강제 종료 처리 방향
- 최종 `ConsultationResponse` 변환 방식
- `StreamEvent` 발행 지점
- `user_messages.md`의 사용자 노출 문구 key 반환 규칙

### Out of scope

- 실제 FastAPI route/service/model 코드 작성
- 실제 LangGraph node/edge 코드 작성
- LLM API client 구현
- DB 또는 영속 checkpoint 구현
- 프론트엔드 화면/타입 수정
- 프롬프트 문구 확정

### 아키텍처 결정

```text
frontend/React
  ├─ POST /consultations
  ├─ GET /consultations/{consultation_id}/events  # SSE
  └─ GET /consultations/{consultation_id}
        │
        ▼
backend/FastAPI 단일 서버
  ├─ Pydantic schema validation
  ├─ in-memory ConsultationState store
  ├─ in-memory SSE event broker
  └─ LangGraph workflow
        ├─ supervisor nodes
        └─ 6 agent nodes
```

- DB 저장은 현재 구현에서 필수 요구사항이 아닙니다.
- LangGraph checkpoint를 쓰더라도 `MemorySaver` 수준의 프로세스 내 보관으로 충분합니다.
- 서버 재시작 후 상담 복구는 현재 구현에서 지원하지 않습니다.

## 3. 전체 그래프 토폴로지

`supervisor_protocol.md`의 토폴로지를 구현 기준으로 사용합니다.

```text
START
  │
  ▼
[receive_request]
  │
  ▼
[initialize_state]
  │
  ▼
[analyze_question]                ── 슈퍼바이저 호출 #1
  │
  ▼
[round_1_fanout]                  ── 6개 Agent 병렬 호출
  │   ├── agent_realist
  │   ├── agent_empath
  │   ├── agent_analyst
  │   ├── agent_actor
  │   ├── agent_mediator
  │   └── agent_friend
  ▼
[round_1_join]
  │
  ▼
[summarize_round_1]               ── 슈퍼바이저 호출 #2
  │
  ▼
[round_2_sequential]              ── 6개 Agent 순차 호출
  │
  ▼
[classify_round_2]                ── 슈퍼바이저 호출 #3
  │
  ├── classify_2.payload.next_action == "skip_to_final"
  │      ▼
  │   [integrate_final]            ── 슈퍼바이저 호출 #4
  │      ▼
  │     END
  │
  └── classify_2.payload.next_action == "proceed_to_round_3"
         ▼
      [round_3_sequential]
         │
         ▼
      [integrate_final]            ── 슈퍼바이저 호출 #4
         │
         ▼
        END
```

모든 노드는 실패 시 가능한 한 `[handle_failure]`로 이동합니다. 단, `SAFETY_BLOCKED`는 즉시 안전 종료합니다.

## 4. 중심 상태 객체

워크플로우의 단일 source of truth는 `ConsultationState`입니다.

```python
class ConsultationState(TypedDict):
    consultation_id: str
    started_at: str
    updated_at: str
    status: ConsultationStatus
    schema_version: Literal["1.0.0"]

    user_question: str
    language: Literal["ko-KR"]

    analysis: NotRequired[QuestionAnalysis]
    summary_1: NotRequired[SupervisorNote]
    classify_2: NotRequired[SupervisorNote]
    final_summary: NotRequired[SupervisorNote]

    round_1_opinions: list[AgentOpinion]
    round_2_rebuttals: list[AgentRebuttal]
    round_3_positions: list[AgentFinalPosition]

    errors: list[ErrorEvent]
    skipped_agents: list[SkippedAgent]
    termination: NotRequired[Termination]
```

Reducer 정책:

| 필드 | 정책 |
| --- | --- |
| `round_1_opinions`, `round_2_rebuttals`, `round_3_positions` | `append_unique_by_id` |
| `errors`, `skipped_agents` | append |
| `analysis`, `summary_1`, `classify_2`, `final_summary` | last-write-wins |
| `status`, `updated_at` | last-write-wins |

## 5. 노드 계약

| 노드 | 상태값 | 입력 | 출력 | 성공 시 다음 | 실패 시 다음 |
| --- | --- | --- | --- | --- | --- |
| `receive_request` | `pending` | `UserConsultationRequest` | request 검증 결과 | `initialize_state` | 400 응답 |
| `initialize_state` | `pending` | request | 빈 `ConsultationState` | `analyze_question` | `failed` |
| `analyze_question` | `analyzing` | `user_question`, `language` | `analysis` | `round_1_fanout` | `handle_failure` 또는 안전 종료 |
| `round_1_fanout` | `round_1_running` | `analysis`, Agent persona | `round_1_opinions[]` | `round_1_join` | 부분 실패 기록 후 join |
| `round_1_join` | `round_1_running` | `round_1_opinions` | 라운드 생존 수 판단 | `summarize_round_1` | `handle_failure` |
| `summarize_round_1` | `summary_1_running` | `analysis`, `round_1_opinions` | `summary_1` | `round_2_sequential` | `handle_failure` |
| `round_2_sequential` | `round_2_running` | `analysis`, `summary_1`, 1라운드 메시지 | `round_2_rebuttals[]` | `classify_round_2` | 부분 실패 기록 후 classify |
| `classify_round_2` | `classify_2_running` | `summary_1`, `round_2_rebuttals` | `classify_2` | `integrate_final` 또는 `round_3_sequential` | `handle_failure` |
| `round_3_sequential` | `round_3_running` | `analysis`, `summary_1`, `classify_2`, 이전 발언 | `round_3_positions[]` | `integrate_final` | 가능한 한 `integrate_final` |
| `integrate_final` | `summarizing` | 요약/분류/최종입장 | `final_summary` | `completed`/`terminated` | fallback final 또는 `failed` |
| `handle_failure` | 상황별 | 오류 상태 | `errors`, `skipped_agents`, `termination` | 가능한 한 `integrate_final` | `failed` |

## 6. Conditional edge 조건

| 위치 | 조건 | 다음 노드 |
| --- | --- | --- |
| `analyze_question` 이후 | `analysis` 정상 | `round_1_fanout` |
| `analyze_question` 이후 | `SAFETY_BLOCKED` | 안전 종료 |
| `round_1_join` 이후 | `len(round_1_opinions) >= 4` | `summarize_round_1` |
| `round_1_join` 이후 | `len(round_1_opinions) < 4` | `handle_failure` |
| `summarize_round_1` 이후 | `summary_1` 정상 | `round_2_sequential` |
| `summarize_round_1` 이후 | `summary_1` 실패 | `handle_failure` |
| `classify_round_2` 이후 | `next_action == "skip_to_final"` | `integrate_final` + `termination.reason = "consensus_reached"` |
| `classify_round_2` 이후 | `next_action == "proceed_to_round_3"` | `round_3_sequential` |
| `classify_round_2` 이후 | `classify_2` 실패 또는 `len(round_2_rebuttals) < 4` | `handle_failure` |
| `round_3_sequential` 이후 | 항상 | `integrate_final` |

## 7. JSON 생성 책임 분리

LLM은 각 프롬프트 출력 블록의 JSON만 생성합니다. 워크플로우는 운영 메타데이터를 채웁니다.

| 주체 | 채우는 필드 |
| --- | --- |
| LLM | `advice`, `rationale`, `stance`, `confidence`, `key_points` 등 라운드별 본문 필드 |
| 워크플로우 | `id`, `created_at`, `consultation_id`, `round`, `agent_id`, `agent_name`, `language`, `schema_version` |
| 백엔드 응답 변환기 | `PublicRound`, `PublicFinalSummary`, `PublicError`, `PublicTermination` |

검증 실패 시에는 원문을 그대로 노출하지 않고 `ErrorEvent.detail`에 디버그용으로만 보관합니다.

## 8. 실패/재시도/스킵 정책

| 오류 | 재시도 | 실패 시 처리 |
| --- | --- | --- |
| `LLM_TIMEOUT` | 1회 | 해당 발언 스킵, `errors` 기록 |
| `LLM_RATE_LIMIT` | 2회, 1s/4s backoff | 워크플로우 `timeout` 종료 |
| `JSON_PARSE_FAILED` | 1회, `retry.json_only` 주입 | 해당 발언 스킵 |
| `SCHEMA_VIOLATION` | 1회, `retry.schema_violation` 주입 | 해당 발언 스킵 |
| `PERSONA_DRIFT` | 1회, `retry.persona_reinforce` 주입 | 스킵 + 누적 카운트 |
| `SAFETY_BLOCKED` | 없음 | 즉시 안전 종료 |

`integrate_final`은 실패하더라도 마지막 사용 가능한 상태를 이용해 fallback final을 생성해야 합니다.

## 9. 응답 변환 계약

백엔드는 사용자에게 `ConsultationState` 원본을 그대로 반환하지 않습니다. 항상 `ConsultationResponse`로 가공합니다.

```python
def build_consultation_response(state: ConsultationState) -> ConsultationResponse:
    return {
        "consultation_id": state["consultation_id"],
        "status": state["status"],
        "started_at": state["started_at"],
        "completed_at": state.get("updated_at") if state["status"] in ["completed", "terminated", "failed"] else None,
        "user_question": state["user_question"],
        "language": state["language"],
        "analysis": to_public_analysis(state.get("analysis")),
        "rounds": build_public_rounds(state),
        "final": to_public_final_summary(state.get("final_summary"), state["skipped_agents"]),
        "termination": to_public_termination(state.get("termination")),
        "errors": [to_public_error(error) for error in state["errors"] if is_user_visible(error)],
    }
```

주의:

- `PublicError`는 한국어 문구가 아니라 `user_message_key`만 담습니다.
- `PublicTermination.user_message_key`도 문구 키만 담습니다.
- `contributing_agents`는 스킵된 Agent를 제외합니다.

## 10. SSE 스트리밍 이벤트 발행 지점

프론트가 각 stage/agent 결과를 즉시 표시할 수 있도록 FastAPI SSE endpoint에서 아래 `StreamEvent`를 발행합니다.

| 시점 | `event_type` | payload |
| --- | --- | --- |
| 상태 변경 | `status_changed` | `{ "status": ConsultationStatus }` |
| 분석 완료 | `analysis_completed` | `{ "analysis": QuestionAnalysis }` |
| Agent 발언 추가 | `agent_message_added` | `{ "round": RoundType, "message": ... }` |
| Supervisor note 추가 | `supervisor_note_added` | `{ "note": SupervisorNote }` |
| 오류 발생 | `error_occurred` | `{ "error": PublicError }` |
| 최종 완료 | `completed` | `{ "response": ConsultationResponse }` |

SSE가 끊기거나 미지원인 경우 프론트는 `GET /consultations/{consultation_id}`를 폴링합니다.

## 11. API 연결 의사코드

### 11.1 Endpoint 계약

| Method | Path | 목적 | 비고 |
| --- | --- | --- | --- |
| `POST` | `/consultations` | 상담 세션 생성 및 workflow 시작 | 즉시 `{ consultation_id, status }` 반환 |
| `GET` | `/consultations/{consultation_id}` | 현재/최종 `ConsultationResponse` 조회 | SSE fallback/polling |
| `GET` | `/consultations/{consultation_id}/events` | `StreamEvent` SSE 구독 | per-agent/stage 실시간 표시 |

`POST /consultations`는 긴 LLM workflow 완료까지 blocking하지 않습니다. 상태를 만들고 background task를 시작한 뒤, 프론트는 SSE로 부분 결과를 받습니다.

```python
class ConsultationStartResponse(TypedDict):
    consultation_id: str
    status: ConsultationStatus


def post_consultations(request: UserConsultationRequest, background_tasks) -> ConsultationStartResponse:
    validate_request(request)

    existing = store.get(request["consultation_id"])
    if existing is not None:
        return {
            "consultation_id": existing["consultation_id"],
            "status": existing["status"],
        }

    state = initialize_state(request)
    store.save(state)
    event_broker.create_stream(state["consultation_id"])
    event_broker.publish(state["consultation_id"], make_status_event(state))

    background_tasks.add_task(run_workflow_and_publish_events, state["consultation_id"])

    return {
        "consultation_id": state["consultation_id"],
        "status": state["status"],
    }


def get_consultation(consultation_id: str) -> ConsultationResponse:
    state = store.get_or_404(consultation_id)
    return build_consultation_response(state)


async def stream_consultation_events(consultation_id: str):
    store.get_or_404(consultation_id)

    async for event in event_broker.subscribe(consultation_id):
        yield encode_sse(event)

        if event["event_type"] == "completed":
            break
```

## 12. 워크플로우 실행 의사코드

```python
def run_consultation_workflow(state: ConsultationState) -> ConsultationState:
    try:
        publish_status(state, "analyzing")
        state = analyze_question(state)
        publish_event("analysis_completed", {"analysis": state["analysis"]})

        if state.get("termination", {}).get("reason") == "safety_filter":
            return finish_safety_blocked(state)

        publish_status(state, "round_1_running")
        state = run_round_1_fanout(state)
        publish_agent_events("round_1", state["round_1_opinions"])

        if len(state["round_1_opinions"]) < 4:
            return handle_failure(state, reason="internal_error", where="round_1_join")

        publish_status(state, "summary_1_running")
        state = summarize_round_1(state)
        publish_event("supervisor_note_added", {"note": state["summary_1"]})

        publish_status(state, "round_2_running")
        state = run_round_2_sequential(state)
        publish_agent_events("round_2", state["round_2_rebuttals"])

        if len(state["round_2_rebuttals"]) < 4:
            return handle_failure(state, reason="internal_error", where="round_2_sequential")

        publish_status(state, "classify_2_running")
        state = classify_round_2(state)
        publish_event("supervisor_note_added", {"note": state["classify_2"]})
        next_action = state["classify_2"]["payload"]["next_action"]

        if next_action == "skip_to_final":
            state["termination"] = make_termination("consensus_reached")
            publish_status(state, "summarizing")
            final_state = integrate_final(state, status="terminated")
            publish_event("completed", {"response": build_consultation_response(final_state)})
            return final_state

        publish_status(state, "round_3_running")
        state = run_round_3_sequential(state)
        publish_agent_events("round_3", state["round_3_positions"])

        publish_status(state, "summarizing")
        final_state = integrate_final(state, status="completed")
        publish_event("completed", {"response": build_consultation_response(final_state)})
        return final_state

    except WorkflowTimeout:
        return handle_failure(state, reason="timeout", where="workflow")
    except Exception as error:
        return handle_failure(state, reason="internal_error", where="workflow", detail=str(error))
```

## 13. LLM 호출 의사코드

```python
def call_llm_with_json_contract(node_name: str, prompt: Prompt, schema: JsonSchema) -> dict:
    retry_policy = retry_policy_for(node_name)

    for attempt in range(retry_policy.max_attempts):
        raw = llm_client.invoke(prompt, timeout_seconds=30)

        try:
            parsed = parse_json_only(raw)
            validate_schema(parsed, schema)
            return parsed
        except JsonParseError:
            if attempt_can_retry(attempt, retry_policy, "JSON_PARSE_FAILED"):
                prompt = prompt.with_retry_instruction("retry.json_only")
                continue
            raise NodeError(code="JSON_PARSE_FAILED", retry_count=attempt)
        except SchemaViolation:
            if attempt_can_retry(attempt, retry_policy, "SCHEMA_VIOLATION"):
                prompt = prompt.with_retry_instruction("retry.schema_violation")
                continue
            raise NodeError(code="SCHEMA_VIOLATION", retry_count=attempt)
```

## 14. 구현 전 검토 체크리스트

- [ ] `message_schema.md`의 enum 값과 필드명을 변경하지 않았다.
- [ ] `supervisor_protocol.md`의 노드명과 edge 조건을 그대로 반영했다.
- [ ] 1라운드는 병렬, 2·3라운드는 순차 호출로 설계했다.
- [ ] 2·3라운드 순서가 `realist → analyst → mediator → empath → actor → friend`로 고정되어 있다.
- [ ] LLM 출력 JSON과 워크플로우 메타 필드의 책임이 분리되어 있다.
- [ ] `ConsultationResponse` 이외의 형태로 프론트에 최종 응답을 반환하지 않는다.
- [ ] 백엔드가 한국어 사용자 문구를 직접 만들지 않고 `*_user_message_key`만 반환한다.
- [ ] `PublicTermination.user_message_key`와 `PublicError.user_message_key`가 `user_messages.md`의 key와 일치한다.
- [ ] `POST /consultations`는 workflow를 blocking하지 않고 start response를 반환한다.
- [ ] SSE가 stage/agent별 `StreamEvent`를 순서대로 발행한다.
- [ ] `JSON_PARSE_FAILED`, `SCHEMA_VIOLATION`, `PERSONA_DRIFT`, `SAFETY_BLOCKED` 처리가 누락되지 않았다.
- [ ] 커밋/푸시는 사용자 검토 후 별도로 결정한다.
