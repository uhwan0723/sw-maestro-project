# Debate Rounds

1~3라운드 토론 진행 규칙과 JSON 입출력 계약입니다. 이 문서는 김민우·신현성 공동 담당 예정 문서이며, 이번 초안은 김민우의 **워크플로우 구현 관점**에서 작성합니다.

## 1. 담당과 기준 문서

| 항목 | 내용 |
| --- | --- |
| 골격 담당 | 김민우 — 호출 순서, 라운드 실행 구조, 데이터 전달 흐름 |
| 프로토콜 담당 | 신현성 — 메시지 스키마, 입출력 규칙, 슈퍼바이저 개입 규칙 |
| 프롬프트 담당 | 임지빈 — 각 Agent/Supervisor prompt가 아래 JSON을 출력하도록 설계 |
| 프론트 확인 | 김준서, 박준혁 — 라운드별 메시지 표시와 사용자 문구 키 확인 |

기준 문서:

- [`message_schema.md`](message_schema.md): `AgentOpinion`, `AgentRebuttal`, `AgentFinalPosition`, `SupervisorNote` 정의
- [`supervisor_protocol.md`](supervisor_protocol.md): 라운드 호출 순서, 합의/충돌/보류 분류, 실패 처리
- [`consultation_workflow.md`](consultation_workflow.md): 전체 그래프에서 각 라운드가 놓이는 위치
- [`../../docs/team44-love-agent/02_user_agent/user_agent_design.md`](../../docs/team44-love-agent/02_user_agent/user_agent_design.md): 6개 Agent 페르소나 표시명

## 2. Agent 목록과 고정 순서

| `agent_id` | 표시명 | 라운드 역할 |
| --- | --- | --- |
| `realist` | 현실주의자 | 행동·결과 중심 의견 |
| `empath` | 공감형 감성론자 | 감정 우선 의견 |
| `analyst` | 신중한 분석가 | 맥락·패턴 분석 |
| `actor` | 행동파 조언자 | 실행 행동 제안 |
| `mediator` | 균형형 중재자 | 양측 고려·중재 |
| `friend` | 친구형 상담자 | 캐주얼한 친구 관점 |

2·3라운드 순차 호출 순서:

```text
realist → analyst → mediator → empath → actor → friend
```

사유: 직설·논리·중립 관점이 먼저 쟁점을 만들고, 감정·행동·친구 관점이 후반에 보완할 수 있게 합니다.

## 3. 라운드 전체 요약

| 라운드 | 호출 방식 | 입력 | LLM 출력 | 워크플로우 저장 필드 | 종료 조건 |
| --- | --- | --- | --- | --- | --- |
| 1라운드 | 6개 Agent 병렬 | `analysis` + 자기 persona | `AgentOpinion` 본문 JSON | `round_1_opinions` | 생존 메시지 4개 이상 |
| 슈퍼바이저 요약 | Supervisor 1회 | `analysis`, `round_1_opinions` | `Summary1Payload` | `summary_1` | 정상 생성 |
| 2라운드 | 6개 Agent 순차 | `analysis`, `summary_1`, 1라운드 의견 | `AgentRebuttal` 본문 JSON | `round_2_rebuttals` | 생존 메시지 4개 이상 |
| 슈퍼바이저 분류 | Supervisor 1회 | `summary_1`, `round_2_rebuttals` | `Classify2Payload` | `classify_2` | `next_action` 결정 |
| 3라운드 | 필요 시 6개 Agent 순차 | `analysis`, `summary_1`, `classify_2`, 자기 이전 발언 | `AgentFinalPosition` 본문 JSON | `round_3_positions` | 항상 최종 통합으로 이동 |

## 4. 공통 JSON 원칙

1. 모든 LLM 출력은 JSON만 허용합니다.
2. 자유 텍스트는 반드시 `advice`, `rationale`, `statement`, `final_advice` 같은 명시 필드 안에만 둡니다.
3. 워크플로우가 채우는 메타 필드를 LLM이 임의 생성하지 않습니다.
4. enum 값은 `message_schema.md`의 정의만 사용합니다.
5. 문자열 길이 제한을 초과하면 `SCHEMA_VIOLATION`으로 처리합니다.
6. 잘못된 JSON은 `JSON_PARSE_FAILED`로 처리하고 1회 재시도합니다.

워크플로우가 채우는 공통 필드:

```text
id
created_at
consultation_id
round
agent_id
agent_name
language
```

## 5. 1라운드 — 독립 의견 생성

### 목적

6개 Agent가 서로의 의견을 보지 않고 사용자의 고민을 각자의 페르소나로 해석해 독립 의견을 만듭니다.

### 입력 컨텍스트

| 포함 | 제외 |
| --- | --- |
| `analysis` | 다른 Agent 의견 |
| 자기 `agent_id`, `agent_name`, persona prompt | 토론 요약 |
| `user_question`은 필요 시 `analysis` 안의 요약으로 대체 | 운영 메타, 오류 목록 |

### LLM 출력 JSON

```json
{
  "advice": "답장 텀이 길어진다면 한 번 직접 만나자고 제안해 보세요.",
  "rationale": "텍스트로는 의도 해석이 모호해서 오해가 누적됩니다.",
  "stance": "clarify",
  "confidence": 0.7,
  "key_points": ["텍스트 해석의 모호성", "오프라인 만남의 정보량"]
}
```

### 워크플로우 저장 형태

LLM 출력에 메타 필드를 붙여 `AgentOpinion`으로 저장합니다.

```python
opinion = {
    "id": new_uuid(),
    "created_at": now_utc(),
    "consultation_id": state["consultation_id"],
    "round": "round_1",
    "agent_id": agent_id,
    "agent_name": AGENT_NAMES[agent_id],
    "language": "ko-KR",
    **llm_json,
}
```

### 검증 규칙

- `stance`는 `proceed | pause | withdraw | clarify | mixed` 중 하나여야 합니다.
- `confidence`는 `0.0 <= confidence <= 1.0`입니다.
- `key_points`는 1~3개, 각 60자 이내입니다.
- 6개 중 최소 4개 Agent의 의견이 있어야 다음 단계로 이동합니다.

### 의사코드

```python
def run_round_1_fanout(state):
    state["status"] = "round_1_running"

    results = parallel_map(
        AGENT_IDS,
        lambda agent_id: call_agent_round_1(state["analysis"], agent_id),
        timeout_seconds=120,
    )

    for result in results:
        if result.ok:
            state["round_1_opinions"] = append_unique_by_id(
                state["round_1_opinions"],
                enrich_agent_opinion(result.agent_id, result.json, state),
            )
        else:
            record_agent_error_or_skip(state, result)

    return state
```

## 6. 슈퍼바이저 요약 — `summary_1`

### 목적

1라운드의 수렴점, 발산점, 다음 라운드에서 다룰 질문을 정리합니다.

### 입력

- `analysis`
- 6개 또는 생존 Agent의 `AgentOpinion` 전문

### 출력 JSON

```json
{
  "headline": "답장 텀의 의미를 단정하기보다 관계 확인 행동이 필요하다는 의견이 많습니다.",
  "converging_points": ["답장 텀만으로 관심도를 단정하기 어렵다"],
  "diverging_points": ["먼저 행동할지, 시간을 둘지 의견이 갈린다"],
  "open_questions": ["상대에게 직접 확인하는 행동이 지금 적절한가?"]
}
```

`summary_1`은 이후 라운드에서 1라운드 원문 전체를 대체하는 압축 컨텍스트입니다.

## 7. 2라운드 — 반박/보완

### 목적

각 Agent가 1라운드 의견을 보고 동의, 부분 동의, 반박, 확장 의견을 제시합니다.

### 입력 컨텍스트

| 포함 | 설명 |
| --- | --- |
| `analysis` | 원 질문 해석 결과 |
| `summary_1` | 1라운드 수렴/발산 요약 |
| 자기 1라운드 의견 | 입장 유지/수정 판단용 |
| 다른 Agent 1라운드 의견 ID 목록 + 요약 | `targets` 생성을 위한 참조 |
| 같은 2라운드에서 앞서 발언한 Agent 발언 | 순차 호출상 후행 Agent만 참조 가능 |

### LLM 출력 JSON

```json
{
  "targets": [
    {
      "target_message_id": "4caa0000-0000-4000-8000-000000000001",
      "target_agent_id": "analyst",
      "agreement": "partial"
    }
  ],
  "statement": "분석가의 말처럼 단정은 어렵지만, 계속 기다리기만 하면 사용자의 불안이 커질 수 있습니다.",
  "rationale": "확인 행동은 상대의 마음뿐 아니라 사용자의 감정 소모를 줄이는 기준점이 됩니다.",
  "updated_position": "clarify",
  "new_evidence": ["불확실성이 길어질수록 감정 소모가 커짐"]
}
```

### 중요 검증 규칙

- `targets`는 1~3개입니다.
- `target_message_id`는 같은 `consultation_id`의 이전 라운드 메시지 ID여야 합니다.
- 이름이나 배열 인덱스로 참조하면 안 됩니다.
- `target_agent_id`는 실제 대상 메시지의 `agent_id`와 일치해야 합니다.
- `agreement`는 `agree | partial | disagree | extend` 중 하나입니다.
- `updated_position`은 없거나 `StanceType`이어야 합니다.

### 의사코드

```python
def run_round_2_sequential(state):
    state["status"] = "round_2_running"

    for agent_id in ROUND_SEQUENTIAL_ORDER:
        if should_skip_agent(state, agent_id):
            continue

        context = build_round_2_context(state, agent_id)
        result = call_agent_round_2(context, agent_id)

        if result.ok:
            rebuttal = enrich_agent_rebuttal(result.agent_id, result.json, state)
            validate_targets(rebuttal["targets"], state["round_1_opinions"], state["round_2_rebuttals"])
            state["round_2_rebuttals"] = append_unique_by_id(state["round_2_rebuttals"], rebuttal)
        else:
            record_agent_error_or_skip(state, result)

    return state
```

## 8. 슈퍼바이저 분류 — `classify_2`

### 목적

2라운드 발언을 합의, 충돌, 보류로 분류하고 3라운드 진행 여부를 결정합니다.

### 분류 기준

| 분류 | 조건 |
| --- | --- |
| `consensus` | 6개 중 5개 이상이 동일하거나 호환 가능한 결론 |
| `conflict` | `agree` 진영과 `disagree` 진영이 각각 2개 이상 |
| `pending` | 위 둘 모두 아닌 경우 |

### `consensus_ratio`

```text
consensus_ratio = consensus 항목 수 / (consensus + conflict + pending 항목 수)
```

분모가 0이면 `consensus_ratio = 0.0`으로 두고 `pending`에 `"미도출"` 항목을 추가합니다.

### 출력 JSON

```json
{
  "consensus": [
    {
      "topic": "답장 텀만으로 관심도를 단정하지 않는다",
      "supporting_message_ids": ["..."]
    }
  ],
  "conflict": [],
  "pending": [
    {
      "topic": "먼저 약속을 제안할 시점",
      "supporting_message_ids": ["..."]
    }
  ],
  "consensus_ratio": 0.5,
  "next_action": "proceed_to_round_3"
}
```

### 다음 단계 결정

| 조건 | `next_action` |
| --- | --- |
| `consensus_ratio >= 0.7` 그리고 `conflict.length == 0` | `skip_to_final` |
| 그 외 | `proceed_to_round_3` |

## 9. 3라운드 — 최종 입장 정리

### 목적

충돌 또는 보류가 남았을 때 각 Agent가 최종 입장과 행동 제안을 정리합니다.

### 실행 조건

`classify_2.payload.next_action == "proceed_to_round_3"`일 때만 실행합니다.

### 입력 컨텍스트

- `analysis`
- `summary_1`
- `classify_2`
- 자기 1라운드 의견
- 자기 2라운드 발언
- 같은 3라운드에서 앞서 발언한 Agent 최종 입장

### LLM 출력 JSON

```json
{
  "final_stance": "clarify",
  "final_advice": "상대의 답장 속도만 해석하지 말고 가벼운 약속을 제안해 반응을 확인해 보세요.",
  "changed_from_round_1": false,
  "change_reason": null,
  "action_items": ["가벼운 만남 제안하기", "상대 반응을 기준으로 다음 행동 정하기"]
}
```

### 검증 규칙

- `final_stance`는 `StanceType`입니다.
- `changed_from_round_1 == true`이면 `change_reason`이 필수입니다.
- `action_items`는 0~3개, 각 80자 이내입니다.

### 의사코드

```python
def run_round_3_sequential(state):
    state["status"] = "round_3_running"

    for agent_id in ROUND_SEQUENTIAL_ORDER:
        if should_skip_agent(state, agent_id):
            continue

        context = build_round_3_context(state, agent_id)
        result = call_agent_round_3(context, agent_id)

        if result.ok:
            position = enrich_agent_final_position(result.agent_id, result.json, state)
            validate_changed_from_round_1(position, state["round_1_opinions"])
            state["round_3_positions"] = append_unique_by_id(state["round_3_positions"], position)
        else:
            record_agent_error_or_skip(state, result)

    return state
```

## 10. 최종 통합 입력

`integrate_final`은 다음 중 가능한 자료를 사용합니다.

| 상황 | 최종 통합 입력 |
| --- | --- |
| 3라운드 수행 | `analysis`, `summary_1`, `classify_2`, `round_3_positions` |
| 3라운드 생략 | `analysis`, `summary_1`, `classify_2`, `round_2_rebuttals` 요약 |
| 일부 Agent 스킵 | 살아남은 Agent 발언만 사용, 스킵 사실은 사용자에게 직접 노출하지 않음 |
| 안전 필터 | 고정 safety final payload 사용 |

최종 출력은 `FinalPayload`입니다.

```json
{
  "situation": "사용자는 썸 관계에서 답장 텀이 늦어져 관심이 식은 것인지 고민하고 있습니다.",
  "disagreements": ["먼저 행동할지, 조금 더 관찰할지에 대한 의견 차이"],
  "final_advice": "답장 속도만으로 결론 내리기보다 가벼운 약속을 제안해 상대의 반응을 확인해 보세요.",
  "action_items": [
    {
      "title": "가벼운 만남 제안",
      "detail": "부담 없는 시간과 장소로 짧게 만나자고 말해 반응을 봅니다.",
      "timing": "immediate"
    }
  ],
  "caveats": ["상대의 상황을 단정하지 않기"]
}
```

## 11. 라운드 종료/강제 종료 조건

| 조건 | 처리 |
| --- | --- |
| 1라운드 생존 Agent 4명 미만 | `internal_error`로 `handle_failure` |
| 2라운드 생존 Agent 4명 미만 | `internal_error`로 `handle_failure` |
| `consensus_ratio >= 0.7` + conflict 없음 | 3라운드 생략, `consensus_reached` |
| 동일 의견 반복 감지 | 가능한 한 `integrate_final` |
| Agent 3명 이상 영구 스킵 | `persona_breakdown` |
| 전체 타임아웃 | 가능한 마지막 자료로 `integrate_final`, 불가능하면 `failed` |
| 안전 필터 차단 | 즉시 안전 종료 |

## 12. 프론트 전달 구조와 라운드 묶음

프론트는 `ConsultationResponse.rounds`를 통해 라운드별 메시지를 표시합니다.

```python
def build_public_rounds(state):
    rounds = []

    if state["round_1_opinions"]:
        rounds.append({
            "round": "round_1",
            "started_at": infer_started_at(state["round_1_opinions"]),
            "completed_at": infer_completed_at(state["round_1_opinions"]),
            "messages": state["round_1_opinions"],
            "supervisor_note": state.get("summary_1"),
        })

    if state["round_2_rebuttals"]:
        rounds.append({
            "round": "round_2",
            "started_at": infer_started_at(state["round_2_rebuttals"]),
            "completed_at": infer_completed_at(state["round_2_rebuttals"]),
            "messages": state["round_2_rebuttals"],
            "supervisor_note": state.get("classify_2"),
        })

    if state["round_3_positions"]:
        rounds.append({
            "round": "round_3",
            "started_at": infer_started_at(state["round_3_positions"]),
            "completed_at": infer_completed_at(state["round_3_positions"]),
            "messages": state["round_3_positions"],
        })

    return rounds
```

주의:

- 프론트 토론 로그의 화살표는 `AgentRebuttal.targets[*].target_message_id` 기준으로 그립니다.
- 백엔드는 사용자 문구를 직접 만들지 않고 문구 키만 내려줍니다.
- `summary_1`과 `classify_2`는 라운드 이해를 돕는 supervisor note로 묶어 전달할 수 있습니다.

## 13. 테스트 시나리오 초안

| 시나리오 | 입력/조건 | 기대 결과 |
| --- | --- | --- |
| 정상 3라운드 | 합의율 0.7 미만 | `round_3_positions` 생성 후 `completed` |
| 2라운드 합의 | `consensus_ratio >= 0.7`, conflict 없음 | 3라운드 생략, `terminated`, `consensus_reached` |
| 1라운드 일부 실패 | Agent 1~2명 실패 | 살아남은 메시지로 계속 진행 |
| 1라운드 다수 실패 | 생존 3명 이하 | `internal_error` 처리 |
| JSON 오류 | 잘못된 LLM JSON | 1회 재시도 후 스킵 또는 성공 |
| schema 오류 | enum/길이 위반 | 1회 재시도 후 스킵 또는 성공 |
| persona drift | 역할 이탈 | 1회 재시도, 반복 시 스킵 카운트 |
| safety blocked | 안전 필터 차단 | 안전 종료 payload 반환 |

## 14. 구현 전 검토 체크리스트

- [ ] 각 라운드의 LLM 출력 JSON이 `message_schema.md` §12와 일치한다.
- [ ] 2라운드 `targets`가 메시지 ID 기반 참조임을 명시했다.
- [ ] 2·3라운드 순차 호출 순서가 고정되어 있다.
- [ ] 1라운드 fanout과 join의 생존 기준이 명시되어 있다.
- [ ] `summary_1`과 `classify_2`가 이후 라운드 컨텍스트로 어떻게 쓰이는지 명시되어 있다.
- [ ] 3라운드 생략 조건이 `classify_2.payload.next_action`과 연결되어 있다.
- [ ] 최종 통합이 3라운드가 없어도 동작해야 함을 명시했다.
- [ ] 프론트 표시용 라운드 묶음과 토론 화살표 기준을 설명했다.
- [ ] 실제 프롬프트 문구는 임지빈, schema 변경은 신현성 검토가 필요함을 유지했다.
