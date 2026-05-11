# Supervisor Protocol

슈퍼바이저 개입 시점, 충돌·합의·보류 분류 규칙, LangGraph conditional edge 조건, 강제 종료·실패 처리 규칙을 정의합니다.

- 주 담당: 신현성
- 사용자: 김민우(LangGraph 그래프 구현), 임지빈(슈퍼바이저 프롬프트 출력 형식 일치)
- 데이터 정의는 [message_schema.md](message_schema.md) 참조. 본 문서는 **언제·왜·어떻게 결정하는가**에 집중.

---

## 1. 그래프 토폴로지

LangGraph 노드와 엣지의 전체 모양. 김민우님의 `consultation_workflow.md`와 일치해야 합니다.

```text
START
  │
  ▼
[analyze_question]                ── 슈퍼바이저 호출 #1
  │
  ▼
[round_1_fanout]                  ── 6개 에이전트 병렬 호출
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
[round_2_sequential]              ── 6개 에이전트 순차 호출
  │
  ▼
[classify_round_2]                ── 슈퍼바이저 호출 #3
  │
  ├──(consensus_ratio ≥ 0.7)──▶ [integrate_final] ──▶ END
  │
  └──(else) ────────────────▶ [round_3_sequential]
                                 │
                                 ▼
                              [integrate_final]   ── 슈퍼바이저 호출 #4
                                 │
                                 ▼
                                END
```

> 각 노드는 실패 시 `[handle_failure]` 노드로 분기하며, 그 노드는 `Termination`을 채우고 가능한 한 `integrate_final`로 회수한다(§7).

---

## 2. 슈퍼바이저 개입 시점

슈퍼바이저는 워크플로우 동안 **정확히 4번** 호출됩니다. 각 호출의 입력·출력·LangGraph 매핑을 명시.

| # | 노드명 | `mode` | 입력 (state에서 읽는 키) | 출력 (state에 쓰는 키) | 목적 |
| --- | --- | --- | --- | --- | --- |
| 1 | `analyze_question` | `analysis` | `user_question`, `language` | `analysis: QuestionAnalysis` | 사용자 고민의 관계 상태·갈등 유형·핵심 이슈 추출, 토론 목표 설정 |
| 2 | `summarize_round_1` | `summary_1` | `analysis`, `round_1_opinions` | `summary_1: SupervisorNote` | 6개 의견의 수렴·발산 지점 정리, 다음 라운드의 질문 도출 |
| 3 | `classify_round_2` | `classify_2` | `summary_1`, `round_2_rebuttals` | `classify_2: SupervisorNote` | 합의·충돌·보류 3분류, 3라운드 진행 여부 결정 |
| 4 | `integrate_final` | `final` | `analysis`, `summary_1`, `classify_2`, `round_3_positions`(존재 시) | `final_summary: SupervisorNote` | 최종 통합 답변 생성 |

### 2.1 슈퍼바이저 입력 컨텍스트 정책

LLM 토큰 절약을 위해 각 호출에 넘기는 컨텍스트 범위를 명시.

| 호출 # | 포함 | 제외 |
| --- | --- | --- |
| 1 | `user_question` 원문 | 그 외 모두 |
| 2 | `analysis`, 6개 `AgentOpinion` 전문 | 운영 메타(`errors`, `skipped_agents`) |
| 3 | `summary_1`, 6개 `AgentRebuttal` 전문 | 1라운드 의견 원문(요약된 `summary_1`로 대체) |
| 4 | `analysis`, `summary_1`, `classify_2`, 3라운드 포지션 또는 2라운드 결과 | 1·2라운드 발언 원문 (요약본만 사용) |

> 각 호출 후 슈퍼바이저는 `SupervisorNote`만 반환하며, **그 안에 다음 호출이 필요로 하는 정보가 모두 들어가야 한다.** 하위 라운드에서 슈퍼바이저 요약을 다시 생성하지 않는다.

---

## 3. 에이전트 호출 규칙

| 항목 | 1라운드 | 2라운드 | 3라운드 |
| --- | --- | --- | --- |
| 동시성 | **병렬** (모두 동시) | **순차** (정해진 순서) | **순차** |
| 에이전트별 입력 | `analysis` + 자기 페르소나 | `analysis`, `summary_1`, 자기의 1라운드 의견, 다른 에이전트 1라운드 의견 ID 목록 + 요약 | `analysis`, `summary_1`, `classify_2`, 자기의 1·2라운드 발언, 합의·충돌 항목 |
| 출력 | `AgentOpinion` | `AgentRebuttal` | `AgentFinalPosition` |
| 발언 1회당 토큰 상한(권장) | 600 | 800 | 600 |
| 호출 타임아웃 | 30초 | 30초 | 30초 |

### 3.1 순차 라운드의 호출 순서

순차 라운드(2·3)에서 에이전트 호출 순서는 다음으로 고정:

```text
realist → analyst → mediator → empath → actor → friend
```

> 사유: 직설·논리·중립 → 감정·행동·캐주얼 순으로 진행하면 후반 에이전트가 앞 의견을 참조하여 보완하기 쉬움. 같은 페르소나끼리 인접하지 않게 배치.

각 에이전트는 자기보다 앞서 발언한 같은 라운드 동료의 발언도 참조 가능하다 (`targets`에 포함 가능).

### 3.2 발언 권한

- 1라운드: 6개 에이전트만 발언. 슈퍼바이저는 발언 안 함.
- 2·3라운드: 6개 에이전트만 발언. 슈퍼바이저는 라운드 종료 후에만 노트 작성.
- 슈퍼바이저는 에이전트 발언을 수정할 수 없다. 잘못된 발언은 스킵 또는 재생성으로만 처리(§7).

---

## 4. 충돌·합의·보류 분류 규칙

`classify_round_2` 노드(슈퍼바이저 호출 #3)에서 적용하는 분류 기준.

### 4.1 분류 기준

각 `topic`(쟁점)을 다음 규칙으로 분류:

| 분류 | 조건 |
| --- | --- |
| `consensus` | 6개 에이전트 중 **5개 이상**이 동일하거나 호환 가능한 `final_stance` 또는 `agreement` 표현 (예: `agree` + `partial` 모두 합의로 본다) |
| `conflict` | `agree` 진영과 `disagree` 진영이 각각 **2개 이상** |
| `pending` | 위 둘 모두 아닌 경우 (예: `extend` 발언이 절반 이상이거나, 의견이 4-2로 갈리는 경우) |

> "호환 가능"은 슈퍼바이저 LLM의 판단에 위임. 다만 이진 enum(`proceed` ↔ `withdraw`)은 자동으로 비호환.

### 4.2 `consensus_ratio` 계산

```text
consensus_ratio = (consensus 항목 수) / (consensus + conflict + pending 항목 수)
```

분모가 0이면 (즉 어떤 쟁점도 도출되지 않으면) `consensus_ratio = 0.0`으로 두고 `pending`에 `"미도출"` 항목 1개 추가.

### 4.3 `next_action` 결정

| 조건 | `next_action` |
| --- | --- |
| `consensus_ratio ≥ 0.7` **및** `conflict.length == 0` | `skip_to_final` |
| 그 외 | `proceed_to_round_3` |

> 임계 0.7은 PoC 기본값. 운영 시 0.6~0.8 사이 조정 가능. 변경 시 `meta.consensus_threshold`에 기록.

---

## 5. Conditional Edge 조건

LangGraph `add_conditional_edges` 매핑. 김민우님이 그래프 구성 시 그대로 사용.

### 5.1 `analyze_question` 이후

| 조건 | 다음 노드 |
| --- | --- |
| `analysis` 정상 | `round_1_fanout` |
| `analysis` 실패 (`SAFETY_BLOCKED` 등) | `handle_failure` |

### 5.2 `round_1_join` 이후

| 조건 | 다음 노드 |
| --- | --- |
| `len(round_1_opinions) ≥ 4` | `summarize_round_1` |
| `len(round_1_opinions) < 4` | `handle_failure` (이유: `internal_error`) |

> 6개 에이전트 중 최소 4개가 살아남아야 토론 의미가 있다는 정책. 임계값은 [agents/prompts/](../prompts/)와 [backend/](../../backend/) 운영 경험에 따라 조정.

### 5.3 `summarize_round_1` 이후

| 조건 | 다음 노드 |
| --- | --- |
| `summary_1` 정상 | `round_2_sequential` |
| `summary_1` 실패 | `handle_failure` |

### 5.4 `classify_round_2` 이후

| 조건 | 다음 노드 |
| --- | --- |
| `classify_2.payload.next_action == "skip_to_final"` | `integrate_final` (3라운드 생략, `Termination.reason = "consensus_reached"`) |
| `classify_2.payload.next_action == "proceed_to_round_3"` | `round_3_sequential` |
| `classify_2` 실패 또는 `len(round_2_rebuttals) < 4` | `handle_failure` |

### 5.5 `round_3_sequential` 이후

| 조건 | 다음 노드 |
| --- | --- |
| 항상 | `integrate_final` |

`integrate_final`은 `round_3_positions`가 비어 있어도 동작해야 함(2라운드 자료만으로 통합 가능).

---

## 6. 강제 종료 조건

워크플로우를 정상 흐름에서 이탈시켜 조기 종료하는 조건. 어떤 노드에서든 감지되면 `Termination`을 채우고 가능한 한 `integrate_final`로 회수한다.

### 6.1 종료 트리거 표

| 트리거 | 감지 위치 | `TerminationReason` | 처리 |
| --- | --- | --- | --- |
| 안전 필터 차단 | `analyze_question` 또는 어느 에이전트 호출 | `safety_filter` | 즉시 `END`. `final_summary`는 안전 가드 메시지로 채움(§6.5) |
| 동일 의견 반복 | `summarize_round_1` 또는 `classify_round_2` | `repetition_detected` | 가능한 한 즉시 `integrate_final` |
| 라운드 한도 초과 | `classify_round_2` 후 `consensus_ratio < 0.3` 이면서 라운드 3 이미 완료 | `round_limit_exceeded` | `integrate_final` |
| 페르소나 붕괴 누적 | `[handle_failure]` 안에서 `skipped_agents` 통계 평가 | `persona_breakdown` | 살아남은 에이전트만으로 `integrate_final` |
| 2라운드 합의 도달 | `classify_round_2` (§5.4) | `consensus_reached` | `integrate_final` |
| 전체 타임아웃 | 워크플로우 외부 감시 | `timeout` | 가능한 한 마지막 가용 자료로 `integrate_final`. 불가능하면 `failed` |
| 복구 불가 오류 | 어디서든 | `internal_error` | `failed`로 종료 |

### 6.2 동일 의견 반복 감지 규칙

다음 중 하나라도 해당하면 트리거:

1. 2라운드 발언 6개 중 **4개 이상**이 자기 1라운드 의견과 `stance` 동일 + `new_evidence == []` + `targets`가 모두 `agree`
2. `summary_1`의 `diverging_points`가 비어 있음 + 1라운드 stance 분포가 단일 값 6개

### 6.3 페르소나 붕괴 감지 규칙

각 에이전트별로 이번 상담에서 누적 `PERSONA_DRIFT` 카운트 유지(§7). 한 에이전트의 누적 카운트가 **2** 이상이면 해당 에이전트를 이후 라운드에서 영구 스킵하고, 영구 스킵된 에이전트가 **3명 이상**이면 워크플로우를 `persona_breakdown`으로 종료.

### 6.4 페르소나 이탈 판정 기준

`PERSONA_DRIFT` 오류는 다음 휴리스틱으로 판정 (1차: 자동, 2차: 슈퍼바이저 검토 — PoC는 자동만):

| 항목 | 기준 |
| --- | --- |
| 페르소나 키워드 미포함 | 해당 에이전트의 톤·관점에 해당하는 핵심 키워드(임지빈님 페르소나 프롬프트에 정의) 0개 출현 |
| 다른 에이전트 모방 | `agent_name`을 자기 발언에 언급 + 그 에이전트 톤으로 발언 |
| 역할 이탈 | 의료·법률·심리 진단 발언, 성적·폭력적 발언 |
| 언어 이탈 | 한국어 외 문자가 30% 초과 |

### 6.5 안전 필터 차단 시 응답

`safety_filter` 종료 시 `final_summary`는 다음 고정 구조로 채운다(박준혁님 문구는 별도 정의):

```python
FinalPayload(
    situation="",
    disagreements=[],
    final_advice="",
    action_items=[],
    caveats=["final.caveat.safety_refused"]   # 박준혁님 문구 사전 키
)
```

`PublicTermination.user_message_key = "termination.safety_refused"`.

---

## 7. 실패 / 재시도 / 스킵 규칙

`[handle_failure]` 노드와 각 에이전트 노드 내부에서 적용.

### 7.1 LLM 호출 실패

| `ErrorCode` | 재시도 | 백오프 | 한도 도달 시 |
| --- | --- | --- | --- |
| `LLM_TIMEOUT` | 1회 재시도 | 즉시 | 해당 발언 스킵, `errors`에 기록 |
| `LLM_RATE_LIMIT` | 2회 재시도 | 지수(1s, 4s) | 워크플로우 `timeout`으로 종료 |
| `JSON_PARSE_FAILED` | 1회 재시도 (프롬프트에 "JSON만 출력" 강조 추가) | 즉시 | 스킵 |
| `SCHEMA_VIOLATION` | 1회 재시도 | 즉시 | 스킵 |
| `PERSONA_DRIFT` | 1회 재시도 (시스템 프롬프트에 페르소나 재강조) | 즉시 | 스킵 + 카운트 +1 (§6.3) |
| `SAFETY_BLOCKED` | **재시도 안 함** | — | 워크플로우 즉시 종료 (§6.5) |

### 7.2 스킵 처리

에이전트가 스킵되면 `state.skipped_agents`에 `SkippedAgent` 1건 추가. 이후 라운드에서:

- 동일 에이전트 재시도 **안 함** (페르소나 붕괴인 경우는 영구 스킵, 일시 오류는 다음 라운드에서 재참여 가능 — 일시/영구 구분은 `errors[*].fatal`로 판단)
- 슈퍼바이저는 스킵된 에이전트가 있다는 사실을 `summary_1` 또는 `final_summary`에 별도로 언급하지 않는다 (사용자 노출 금지)
- `PublicFinalSummary.contributing_agents`에서 제외

### 7.3 재시도 시 프롬프트 가공

재시도 시 김민우님 워크플로우는 다음을 시스템 프롬프트에 추가 주입:

| 사유 | 추가 주입 문구 키 (임지빈님 정의) |
| --- | --- |
| `JSON_PARSE_FAILED` | `retry.json_only` |
| `SCHEMA_VIOLATION` | `retry.schema_violation` |
| `PERSONA_DRIFT` | `retry.persona_reinforce` |

### 7.4 슈퍼바이저 호출 실패

슈퍼바이저 호출은 **2회 재시도**, 그래도 실패하면 워크플로우 `internal_error` 종료.
단 호출 #4(`integrate_final`)는 실패해도 마지막 시도 결과를 폴백으로 사용 (자세한 폴백은 김민우님이 워크플로우에서 정의).

### 7.5 워크플로우 타임아웃

| 항목 | 값 |
| --- | --- |
| 단일 LLM 호출 | 30초 |
| 라운드(병렬 또는 순차 합산) | 120초 |
| 워크플로우 전체 | 5분 |

타임아웃 초과 시 §6.1의 `timeout` 흐름.

---

## 8. 멱등성 / 재실행 / 체크포인트

PoC 범위는 단순 멱등만 보장. 풀 체크포인트는 추후.

### 8.1 멱등성

- 같은 `consultation_id` 재요청 시 백엔드는 기존 결과 반환.
- 진행 중(`*_running`) 상태에서 재요청 시 현재 상태 그대로 반환 (재시작 안 함).

### 8.2 LangGraph 체크포인트 (선택)

LangGraph `MemorySaver` 또는 `SqliteSaver` 사용 시 `thread_id = consultation_id` 매핑.

| 키 | 값 |
| --- | --- |
| `thread_id` | `consultation_id` |
| `checkpoint_ns` | `"consultation"` |

> PoC 1차에는 in-memory 저장만 운영해도 충분. DB 저장은 김민우님 백엔드 설계와 함께 결정.

---

## 9. 관측 / 로깅

### 9.1 필수 로그 시점

| 시점 | 로그 항목 |
| --- | --- |
| 워크플로우 시작 | `consultation_id`, `started_at`, `user_question`(해시) |
| 각 노드 진입 | 노드명, `consultation_id`, `status` |
| 각 노드 종료 | 노드명, 소요 시간(ms), 결과 요약 |
| LLM 호출 | 모델, 토큰 사용량, 소요 시간 |
| 오류 | `ErrorCode`, 노드명, 재시도 카운트 |
| 워크플로우 종료 | `Termination`, 총 소요 시간 |

### 9.2 PII 처리

- `user_question` 원문은 로그에 평문 저장하지 않는다(해시 또는 마스킹). 디버그 모드에서만 평문 허용.
- LLM 입력·출력 전문은 별도 디버그 채널에만, 운영 로그에는 메시지 ID와 길이만.

---

## 10. 다른 담당자에게 주는 계약

본 프로토콜이 다른 영역에 강제하는 사항. 변경 시 합의 필요.

### 10.1 임지빈(프롬프트)

- 모든 라운드 출력 JSON은 [message_schema.md §12](message_schema.md#12-부록--임지빈님-프롬프트-출력-블록-템플릿)의 스키마를 그대로 사용.
- 페르소나 핵심 키워드(§6.4)를 페르소나 문서에 명시.
- 재시도 주입 문구 키 3종(§7.3) 정의.

### 10.2 김민우(워크플로우/백엔드)

- §1의 노드 토폴로지와 §5의 conditional edge 조건을 그대로 구현.
- §3의 호출 순서·동시성·타임아웃 준수.
- §7의 재시도·스킵 규칙 구현.
- 백엔드 응답은 [message_schema.md §8](message_schema.md#8-프론트-응답-객체)의 `ConsultationResponse` 형태로만 반환.

### 10.3 김준서·박준혁(프론트)

- 화면은 `ConsultationStatus`(§message_schema.md §2.5)에 따라 단계 표시.
- 사용자 노출 문구는 모두 `*_user_message_key` 필드의 키를 통해서만 결정 — 백엔드의 한국어 평문 노출 금지.
- 토론 로그의 화살표는 `AgentRebuttal.targets[*].target_message_id` 기준으로 그림.

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 |
| --- | --- | --- |
| 1.0.0 | 2026-05-06 | 초안 작성 (신현성) |
