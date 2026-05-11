# Message Schema

멀티 에이전트 상담 워크플로우의 모든 데이터 구조를 정의하는 단일 출처 문서입니다.

- 주 담당: 신현성
- 사용자: 임지빈(프롬프트 출력), 김민우(워크플로우/백엔드), 김준서·박준혁(프론트)
- 실행 환경: LangGraph (Python) 기준. 필드명은 언어 중립적 `snake_case`.

> 이 문서를 변경하면 [agents/prompts/](../prompts/)의 출력 형식과 [backend/](../../backend/) 응답 모델, [frontend/](../../frontend/)의 타입을 함께 갱신해야 합니다.

---

## 1. 설계 원칙

1. **모든 메시지는 식별자(`id`)와 타임스탬프(`created_at`)를 가진다.** 토론 로그 재생, 디버깅, 프론트 정렬에 필수.
2. **에이전트는 `agent_id`(불변)와 `agent_name`(표시용)을 분리한다.** 페르소나 이름이 바뀌어도 코드/로그가 깨지지 않게.
3. **메시지는 다른 메시지를 ID로 참조한다.** 인덱스나 이름 비교 금지. (라운드 2 반박 시 어떤 의견을 가리키는지 명시)
4. **모든 LLM 출력은 JSON 스키마로 강제한다.** 자유 텍스트는 `advice`, `rationale` 등 명시 필드 안에서만 허용.
5. **확장 필드는 `meta` 객체에 격리한다.** 스키마 호환성을 위해 신규 필드는 `meta`에 먼저 도입.
6. **언어는 한국어(ko-KR) 고정.** `language` 필드를 두되 PoC에서는 `"ko-KR"`만 허용.

---

## 2. Enum 정의

### 2.1 `AgentId`

6개 상담 에이전트 + 슈퍼바이저의 불변 식별자. 표시명은 [02_user_agent/user_agent_design.md:18-27](../../docs/team44-love-agent/02_user_agent/user_agent_design.md#L18-L27) 참조.

| `agent_id` | `agent_name`(표시) | 페르소나 |
| --- | --- | --- |
| `realist` | 현실주의자 | 행동·결과 중심, 직설적 |
| `empath` | 공감형 감성론자 | 감정 우선, 따뜻한 말투 |
| `analyst` | 신중한 분석가 | 맥락·패턴 분석, 차분 |
| `actor` | 행동파 조언자 | 행동 권유, 적극적 |
| `mediator` | 균형형 중재자 | 양측 고려, 중립 |
| `friend` | 친구형 상담자 | 캐주얼, 친근 |
| `supervisor` | 슈퍼바이저 | 통합·조정 |

### 2.2 `StanceType` — 1라운드 의견의 입장

| 값 | 의미 |
| --- | --- |
| `proceed` | 관계를 진전시키는 방향 권유 |
| `pause` | 관망/시간 두기 권유 |
| `withdraw` | 거리두기/관계 정리 권유 |
| `clarify` | 직접 확인/대화 권유 |
| `mixed` | 단일 입장으로 분류 어려움 |

> 입장 분류는 슈퍼바이저의 충돌 분류(§5.2)에 사용된다. PoC 범위에서는 5개 고정.

### 2.3 `AgreementType` — 2·3라운드 반박/보완의 자세

| 값 | 의미 |
| --- | --- |
| `agree` | 대상 의견에 동의 (보강 근거 추가) |
| `partial` | 부분 동의 (조건 또는 보완 제시) |
| `disagree` | 반박 (다른 근거 또는 결론 제시) |
| `extend` | 추가 관점 제시 (찬반 외 새로운 차원) |

### 2.4 `RoundType`

| 값 | 의미 |
| --- | --- |
| `analysis` | 슈퍼바이저 질문 해석 단계 |
| `round_1` | 6개 에이전트 독립 의견 생성 |
| `summary_1` | 슈퍼바이저 1라운드 쟁점 정리 |
| `round_2` | 6개 에이전트 반박/보완 |
| `classify_2` | 슈퍼바이저 충돌·합의·보류 분류 |
| `round_3` | 6개 에이전트 최종 입장 정리 |
| `final` | 슈퍼바이저 최종 통합 |

### 2.5 `ConsultationStatus` — 상담 세션의 진행 상태

| 값 | 의미 | 프론트 표시 권장 |
| --- | --- | --- |
| `pending` | 접수만 됨, 분석 시작 전 | "준비 중" |
| `analyzing` | 슈퍼바이저 질문 해석 중 | "고민 분석 중" |
| `round_1_running` | 1라운드 진행 | "에이전트 의견 모으는 중" |
| `summary_1_running` | 1라운드 요약 중 | "쟁점 정리 중" |
| `round_2_running` | 2라운드 진행 | "토론 중" |
| `classify_2_running` | 충돌 분류 중 | "토론 정리 중" |
| `round_3_running` | 3라운드 진행 | "최종 입장 정리 중" |
| `summarizing` | 최종 통합 중 | "결론 작성 중" |
| `completed` | 정상 종료 | "상담 완료" |
| `terminated` | 강제 종료 (요약은 수행됨) | "상담 완료" |
| `failed` | 복구 불가 실패 | "오류 발생" |

> 박준혁님: 위 표시 문구는 권장값. 실제 문구는 [docs/team44-love-agent/03_features_workflow/](../../docs/team44-love-agent/03_features_workflow/)에서 최종 결정.

### 2.6 `TerminationReason` — 강제 종료 사유

| 값 | 의미 |
| --- | --- |
| `normal` | 모든 라운드 정상 완료 |
| `consensus_reached` | 2라운드 후 합의율 임계 초과로 3라운드 생략 |
| `repetition_detected` | 동일 의견 반복 감지 |
| `round_limit_exceeded` | 최대 라운드 초과 |
| `persona_breakdown` | 페르소나 붕괴 누적 |
| `safety_filter` | 부적절한 입력 감지 |
| `timeout` | 전체 워크플로우 타임아웃 |
| `internal_error` | 복구 불가 오류 |

### 2.7 `ErrorCode` — 부분 실패·내부 오류 코드

| 값 | 의미 | 영향 범위 |
| --- | --- | --- |
| `LLM_TIMEOUT` | 단일 LLM 호출 시간 초과 | 해당 에이전트 발언 |
| `LLM_RATE_LIMIT` | 레이트 리밋 | 재시도 |
| `JSON_PARSE_FAILED` | LLM 출력 파싱 실패 | 해당 에이전트 발언 |
| `SCHEMA_VIOLATION` | 필수 필드 누락 또는 enum 위반 | 해당 에이전트 발언 |
| `PERSONA_DRIFT` | 페르소나 이탈 감지 | 해당 에이전트 발언 |
| `SAFETY_BLOCKED` | 안전 필터 차단 | 워크플로우 종료 |
| `WORKFLOW_TIMEOUT` | 전체 시간 초과 | 워크플로우 종료 |
| `UNKNOWN` | 기타 | 컨텍스트 따라 다름 |

---

## 3. 공통 메타데이터

모든 메시지·상태 객체에 공통으로 들어가는 필드.

```python
class Meta(TypedDict, total=False):
    # 확장 필드를 격리하는 자유 객체. 신규 필드는 일단 여기에 도입한 뒤 정식 필드로 승격.
    pass

class TimestampedMessage(TypedDict):
    id: str                # UUID v4. 메시지 단위 고유.
    created_at: str        # ISO 8601, UTC. 예: "2026-05-06T12:34:56.789Z"
    language: Literal["ko-KR"]
    meta: Meta
```

---

## 4. 입력 객체

### 4.1 `UserConsultationRequest` — 프론트가 백엔드로 보내는 요청

```python
class UserConsultationRequest(TypedDict):
    consultation_id: str          # 클라이언트가 생성한 UUID v4 (idempotency key 겸용)
    user_question: str            # 1자 이상, 최대 4000자
    language: Literal["ko-KR"]
    client_meta: NotRequired[ClientMeta]  # User-Agent, locale 등 운영용

class ClientMeta(TypedDict, total=False):
    user_agent: str
    submitted_at: str             # 클라이언트 시각
```

| 필드 | 필수 | 비고 |
| --- | --- | --- |
| `consultation_id` | ✅ | 동일 ID 재요청 시 백엔드는 기존 결과 반환(idempotent) |
| `user_question` | ✅ | 트리밍 후 비어 있으면 400 |
| `language` | ✅ | PoC는 `"ko-KR"`만 |

### 4.2 `QuestionAnalysis` — 슈퍼바이저의 질문 해석 결과

```python
class QuestionAnalysis(TimestampedMessage):
    consultation_id: str
    relationship_state: Literal[
        "crush", "dating", "long_term", "breakup_aftermath", "ambiguous", "other"
    ]
    conflict_type: Literal[
        "communication_frequency", "trust", "future_alignment",
        "emotional_distance", "external_factor", "ambiguous", "other"
    ]
    key_issues: list[str]         # 핵심 쟁점 1~5개, 각 80자 이내
    user_emotion: Literal[
        "anxious", "confused", "hurt", "hopeful", "angry", "neutral"
    ]
    debate_goal: str              # 토론이 도달해야 할 목표 1문장
```

> [03_features_workflow/features_and_workflow.md:22](../../docs/team44-love-agent/03_features_workflow/features_and_workflow.md#L22)의 "관계 상태, 갈등 유형, 핵심 이슈" 요구를 만족.

---

## 5. 라운드별 출력 메시지

### 5.1 `AgentOpinion` — 1라운드 독립 의견

```python
class AgentOpinion(TimestampedMessage):
    consultation_id: str
    round: Literal["round_1"]
    agent_id: AgentId             # supervisor 제외
    agent_name: str               # 표시용. agent_id로부터 결정되며 변경 불가.
    advice: str                   # 핵심 조언 1~3문장, 최대 400자
    rationale: str                # 근거 1~3문장, 최대 400자
    stance: StanceType            # §2.2
    confidence: float             # 0.0~1.0, 자기 의견에 대한 확신도
    key_points: list[str]         # 1~3개, 각 60자 이내. 토론에서 인용될 수 있는 단위
```

**프롬프트 출력 JSON 예시** (임지빈님 프롬프트 5블록 중 "출력" 블록):

```json
{
  "advice": "답장 텀이 길어진다면 한 번 직접 만나자고 제안해 보세요.",
  "rationale": "텍스트로는 의도 해석이 모호해서 오해가 누적됩니다.",
  "stance": "clarify",
  "confidence": 0.7,
  "key_points": ["텍스트 해석의 모호성", "오프라인 만남의 정보량"]
}
```

> `id`, `created_at`, `consultation_id`, `round`, `agent_id`, `agent_name`, `language`는 워크플로우(김민우)가 채우므로 LLM은 위 5개 필드만 출력하면 됩니다.

### 5.2 `AgentRebuttal` — 2라운드 반박/보완

```python
class AgentRebuttal(TimestampedMessage):
    consultation_id: str
    round: Literal["round_2"]
    agent_id: AgentId
    agent_name: str
    targets: list[TargetReference]  # 1~3개. 어떤 의견에 대한 반응인지 ID로 명시
    statement: str                  # 발언 본문, 최대 500자
    rationale: str                  # 근거, 최대 400자
    updated_position: NotRequired[StanceType]  # 입장이 바뀌었으면 새 값
    new_evidence: list[str]         # 새로 제시한 근거 0~3개

class TargetReference(TypedDict):
    target_message_id: str          # AgentOpinion.id
    target_agent_id: AgentId
    agreement: AgreementType        # §2.3
```

> `targets`는 반드시 `AgentOpinion.id`를 참조. 인덱스나 이름으로 참조 금지.

### 5.3 `AgentFinalPosition` — 3라운드 최종 입장 정리

```python
class AgentFinalPosition(TimestampedMessage):
    consultation_id: str
    round: Literal["round_3"]
    agent_id: AgentId
    agent_name: str
    final_stance: StanceType
    final_advice: str               # 최종 조언, 최대 400자
    changed_from_round_1: bool      # 1라운드 stance와 비교
    change_reason: NotRequired[str]  # changed=true 인 경우 필수, 최대 200자
    action_items: list[str]         # 사용자가 취할 수 있는 행동 0~3개, 각 80자
```

### 5.4 `SupervisorNote` — 슈퍼바이저 출력 (4가지 모드)

슈퍼바이저는 4번 호출되며 모드에 따라 페이로드가 다릅니다.

```python
class SupervisorNote(TimestampedMessage):
    consultation_id: str
    mode: Literal["analysis", "summary_1", "classify_2", "final"]
    payload: AnalysisPayload | Summary1Payload | Classify2Payload | FinalPayload
```

#### 5.4.1 `mode = "analysis"` → `AnalysisPayload`

`QuestionAnalysis` 그대로. (편의상 `payload`에 그대로 임베드)

#### 5.4.2 `mode = "summary_1"` → `Summary1Payload`

```python
class Summary1Payload(TypedDict):
    headline: str                  # 1문장 헤드라인, 최대 100자
    converging_points: list[str]   # 의견이 모이는 지점 0~5개
    diverging_points: list[str]    # 의견이 갈리는 지점 0~5개
    open_questions: list[str]      # 다음 라운드에서 다룰 질문 1~3개
```

#### 5.4.3 `mode = "classify_2"` → `Classify2Payload`

```python
class Classify2Payload(TypedDict):
    consensus: list[ClassifiedItem]  # 합의 항목
    conflict: list[ClassifiedItem]   # 충돌 항목
    pending: list[ClassifiedItem]    # 보류 항목
    consensus_ratio: float           # 0.0~1.0, 다음 단계 분기에 사용
    next_action: Literal["proceed_to_round_3", "skip_to_final"]

class ClassifiedItem(TypedDict):
    topic: str                       # 주제, 최대 100자
    supporting_message_ids: list[str]  # 근거가 되는 메시지 ID들
```

#### 5.4.4 `mode = "final"` → `FinalPayload`

```python
class FinalPayload(TypedDict):
    situation: str                   # 상황 요약, 최대 600자
    disagreements: list[str]         # 에이전트 간 대립점 0~5개
    final_advice: str                # 최종 조언, 최대 800자
    action_items: list[ActionItem]   # 1~5개
    caveats: list[str]               # 한계 또는 주의 0~3개

class ActionItem(TypedDict):
    title: str                       # 짧은 제목, 최대 50자
    detail: str                      # 상세, 최대 200자
    timing: Literal["immediate", "short_term", "long_term"]
```

> [04_technical_design/technical_design.md:46-52](../../docs/team44-love-agent/04_technical_design/technical_design.md#L46-L52)의 "상황 요약 / 의견 대립점 / 최종 조언 및 실행 방안" 3섹션 요구를 충족하고 `caveats`로 안전 가드 추가.

---

## 6. LangGraph State 객체

### 6.1 `ConsultationState`

LangGraph 그래프의 중심 자료구조. 모든 노드가 읽고 쓴다.

```python
from typing import Annotated
from langgraph.graph.message import add_messages

class ConsultationState(TypedDict):
    # ── 식별/메타 ───────────────────────────────────────
    consultation_id: str
    started_at: str
    updated_at: str
    status: ConsultationStatus
    schema_version: Literal["1.0.0"]

    # ── 입력 ────────────────────────────────────────────
    user_question: str
    language: Literal["ko-KR"]

    # ── 슈퍼바이저 산출물 ──────────────────────────────
    analysis: NotRequired[QuestionAnalysis]
    summary_1: NotRequired[SupervisorNote]
    classify_2: NotRequired[SupervisorNote]
    final_summary: NotRequired[SupervisorNote]

    # ── 라운드별 에이전트 산출물 (reducer: append) ────
    round_1_opinions: Annotated[list[AgentOpinion], append_unique_by_id]
    round_2_rebuttals: Annotated[list[AgentRebuttal], append_unique_by_id]
    round_3_positions: Annotated[list[AgentFinalPosition], append_unique_by_id]

    # ── 운영/관측 ──────────────────────────────────────
    errors: Annotated[list[ErrorEvent], append]
    skipped_agents: Annotated[list[SkippedAgent], append]
    termination: NotRequired[Termination]
```

### 6.2 Reducer 정책

LangGraph state에서 동일 키에 여러 노드가 쓸 때 합치는 규칙.

| 필드 | reducer | 사유 |
| --- | --- | --- |
| `round_1_opinions` | `append_unique_by_id` | 6개 에이전트 병렬 호출 결과를 누적. 같은 `id` 중복 방지 |
| `round_2_rebuttals` | `append_unique_by_id` | 동일 |
| `round_3_positions` | `append_unique_by_id` | 동일 |
| `errors` | `append` | 모든 오류 보존 |
| `skipped_agents` | `append` | 스킵된 에이전트 모두 기록 |
| `analysis`, `summary_1`, `classify_2`, `final_summary` | last-write-wins (덮어쓰기) | 슈퍼바이저는 한 번만 쓰는 것이 원칙. 재시도 시 덮어쓰기 |
| `status`, `updated_at` | last-write-wins | 항상 최신값 |

`append_unique_by_id` 의사 구현:

```python
def append_unique_by_id(left: list, right: list) -> list:
    seen = {item["id"] for item in left}
    return left + [item for item in right if item["id"] not in seen]
```

---

## 7. 운영 객체

### 7.1 `ErrorEvent`

```python
class ErrorEvent(TimestampedMessage):
    code: ErrorCode
    where: str                       # 노드명. 예: "round_2.agent_realist"
    detail: str                      # 디버깅용, 사용자에게 노출 금지
    retry_count: int
    fatal: bool                      # 워크플로우 중단 여부
```

### 7.2 `SkippedAgent`

```python
class SkippedAgent(TypedDict):
    agent_id: AgentId
    round: RoundType
    reason: ErrorCode
    occurred_at: str
```

### 7.3 `Termination`

```python
class Termination(TypedDict):
    reason: TerminationReason
    occurred_at: str
    notes: NotRequired[str]
```

---

## 8. 프론트 응답 객체

### 8.1 `ConsultationResponse` — 백엔드가 프론트로 보내는 최종 응답

`ConsultationState`에서 사용자에게 노출 가능한 부분만 가공한 형태.

```python
class ConsultationResponse(TypedDict):
    consultation_id: str
    status: ConsultationStatus
    started_at: str
    completed_at: NotRequired[str]
    user_question: str
    language: Literal["ko-KR"]

    analysis: PublicAnalysis        # QuestionAnalysis에서 디버그 필드 제거
    rounds: list[PublicRound]       # 라운드별 묶음
    final: PublicFinalSummary       # FinalPayload + agent_list
    termination: NotRequired[PublicTermination]
    errors: list[PublicError]       # 사용자에게 보여줄 수 있는 부분만

class PublicRound(TypedDict):
    round: RoundType
    started_at: str
    completed_at: str
    messages: list[AgentOpinion | AgentRebuttal | AgentFinalPosition]
    supervisor_note: NotRequired[SupervisorNote]

class PublicFinalSummary(TypedDict):
    situation: str
    disagreements: list[str]
    final_advice: str
    action_items: list[ActionItem]
    caveats: list[str]
    contributing_agents: list[AgentId]  # 토론에 참여한 에이전트 목록 (스킵 제외)

class PublicTermination(TypedDict):
    reason: TerminationReason
    user_message_key: str            # 박준혁님 문구 사전의 키. 예: "termination.consensus_reached"

class PublicError(TypedDict):
    code: ErrorCode
    user_message_key: str            # 사용자에게 보여줄 메시지의 키
    affected_agent: NotRequired[AgentId]
```

> `*_user_message_key` 필드는 박준혁님이 정의할 문구 사전(추후 `docs/team44-love-agent/03_features_workflow/`에 합의)의 키만 담는다. 백엔드가 직접 한국어 문구를 만들지 않는다.

### 8.2 출력 누락 방지 체크리스트

프론트가 화면을 그릴 때 필요한 모든 정보가 응답에 포함되는지 점검:

| 화면 요소 ([README.md:111-117](../README.md#L111-L117)) | 응답 필드 |
| --- | --- |
| 상담 시작 화면 | (입력만, 응답 불필요) |
| 슈퍼바이저 분석 결과 | `analysis` |
| 6개 에이전트 의견 카드 | `rounds[round_1].messages`, `agent_id`, `agent_name`, `advice`, `rationale`, `stance`, `confidence`, `key_points` |
| 라운드별 토론 진행 상태 | `status`, `rounds[*].started_at/completed_at` |
| 토론 로그 | `rounds[round_2].messages` (`targets` 필드로 화살표 그리기) |
| 최종 상담 결과 | `final.*` |
| 진행 단계 표시 | `status` |
| 오류/재시도/완료 문구 | `errors[*].user_message_key`, `termination.user_message_key` |

---

## 9. 스트리밍 이벤트 (옵션, 권장)

[features_and_workflow.md:33](../../docs/team44-love-agent/03_features_workflow/features_and_workflow.md#L33)의 "실시간 채팅 형태 토론 표시"를 위해 SSE 또는 WebSocket으로 부분 결과를 흘려보내는 경우의 이벤트 타입.

```python
class StreamEvent(TypedDict):
    consultation_id: str
    sequence: int                    # 단조 증가
    event_type: Literal[
        "status_changed",
        "analysis_completed",
        "agent_message_added",
        "supervisor_note_added",
        "error_occurred",
        "completed"
    ]
    payload: dict                    # 이벤트별 페이로드
    emitted_at: str
```

| `event_type` | `payload` 형태 |
| --- | --- |
| `status_changed` | `{"status": ConsultationStatus}` |
| `analysis_completed` | `{"analysis": QuestionAnalysis}` |
| `agent_message_added` | `{"round": RoundType, "message": AgentOpinion \| AgentRebuttal \| AgentFinalPosition}` |
| `supervisor_note_added` | `{"note": SupervisorNote}` |
| `error_occurred` | `{"error": PublicError}` |
| `completed` | `{"response": ConsultationResponse}` |

> 스트리밍 미사용 시 클라이언트는 `GET /consultations/{id}` 폴링.

---

## 10. 검증 규칙

런타임에 강제해야 할 검증.

### 10.1 메시지 단위

1. `id`는 UUID v4 형식.
2. `created_at`은 ISO 8601 UTC.
3. `language == "ko-KR"`.
4. 문자열 길이 제한 위반 시 `SCHEMA_VIOLATION` 오류 후 해당 발언 스킵.
5. enum 값 위반 시 동일.
6. `targets[*].target_message_id`는 동일 `consultation_id`의 이전 라운드 메시지 ID여야 함.

### 10.2 라운드 단위

1. `round_1_opinions`은 supervisor 제외 6개 `agent_id` 모두 1개씩(스킵된 에이전트 제외).
2. `round_2_rebuttals`은 각 에이전트당 정확히 1개(스킵 제외).
3. `round_3_positions`은 각 에이전트당 정확히 1개(스킵 제외).
4. 한 라운드의 메시지가 모두 누락되면 강제 종료(`internal_error`).

### 10.3 슈퍼바이저 단위

1. `mode`별 `payload` 타입이 일치.
2. `Classify2Payload.consensus_ratio ∈ [0.0, 1.0]`.
3. `FinalPayload.action_items.length >= 1`.

---

## 11. 변경 관리

- `schema_version`을 따른다(현재 `"1.0.0"`).
- 호환되지 않는 변경은 메이저 버전 증가 + 마이그레이션 노트 작성.
- 신규 필드는 가능하면 `meta` 객체에 먼저 도입하고, 안정화 후 정식 필드로 승격.
- 이 문서가 변경되면:
  - [agents/prompts/](../prompts/) 출력 형식 점검 (임지빈)
  - [backend/](../../backend/) 응답 모델 점검 (김민우)
  - [frontend/](../../frontend/) 타입 정의 점검 (김준서·박준혁)

---

## 12. 부록 — 임지빈님 프롬프트 출력 블록 템플릿

각 라운드 프롬프트의 "출력" 블록에 그대로 붙여 쓸 수 있는 JSON 스키마 요약. (LLM에 보여주기 위한 압축형)

### 1라운드

```text
출력은 반드시 다음 JSON 스키마를 따른다. 다른 텍스트는 금지한다.
{
  "advice": string (1~3문장, 최대 400자),
  "rationale": string (1~3문장, 최대 400자),
  "stance": "proceed" | "pause" | "withdraw" | "clarify" | "mixed",
  "confidence": number (0.0~1.0),
  "key_points": string[] (1~3개, 각 60자 이내)
}
```

### 2라운드

```text
출력은 반드시 다음 JSON 스키마를 따른다.
{
  "targets": [
    {
      "target_message_id": string,
      "target_agent_id": string,
      "agreement": "agree" | "partial" | "disagree" | "extend"
    }
  ] (1~3개),
  "statement": string (최대 500자),
  "rationale": string (최대 400자),
  "updated_position": "proceed" | "pause" | "withdraw" | "clarify" | "mixed" | null,
  "new_evidence": string[] (0~3개)
}
```

### 3라운드

```text
출력은 반드시 다음 JSON 스키마를 따른다.
{
  "final_stance": "proceed" | "pause" | "withdraw" | "clarify" | "mixed",
  "final_advice": string (최대 400자),
  "changed_from_round_1": boolean,
  "change_reason": string | null (changed=true이면 필수, 최대 200자),
  "action_items": string[] (0~3개, 각 80자)
}
```

### 슈퍼바이저 — 분석 모드

```text
{
  "relationship_state": "crush" | "dating" | "long_term" | "breakup_aftermath" | "ambiguous" | "other",
  "conflict_type": "communication_frequency" | "trust" | "future_alignment" | "emotional_distance" | "external_factor" | "ambiguous" | "other",
  "key_issues": string[] (1~5개, 각 80자 이내),
  "user_emotion": "anxious" | "confused" | "hurt" | "hopeful" | "angry" | "neutral",
  "debate_goal": string (1문장)
}
```

### 슈퍼바이저 — 1라운드 요약

```text
{
  "headline": string (최대 100자),
  "converging_points": string[] (0~5개),
  "diverging_points": string[] (0~5개),
  "open_questions": string[] (1~3개)
}
```

### 슈퍼바이저 — 충돌 분류

```text
{
  "consensus": [{"topic": string, "supporting_message_ids": string[]}],
  "conflict":  [{"topic": string, "supporting_message_ids": string[]}],
  "pending":   [{"topic": string, "supporting_message_ids": string[]}],
  "consensus_ratio": number (0.0~1.0),
  "next_action": "proceed_to_round_3" | "skip_to_final"
}
```

### 슈퍼바이저 — 최종 통합

```text
{
  "situation": string (최대 600자),
  "disagreements": string[] (0~5개),
  "final_advice": string (최대 800자),
  "action_items": [
    {"title": string (최대 50자), "detail": string (최대 200자), "timing": "immediate" | "short_term" | "long_term"}
  ] (1~5개),
  "caveats": string[] (0~3개)
}
```
