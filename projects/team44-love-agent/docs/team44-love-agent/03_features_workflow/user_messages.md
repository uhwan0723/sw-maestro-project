# 사용자 노출 문구 사전

박준혁 담당 문서. 프론트엔드에서 사용자에게 직접 보여주는 문구, 버튼 라벨, 상태 메시지, 오류/완료 안내를 정의한다.

## 작성 원칙

- 사용자가 지금 어떤 단계에 있는지 한 문장으로 알 수 있게 쓴다.
- 감정적으로 예민한 연애 고민을 다루므로 단정, 비난, 조롱, 과도한 확신 표현을 피한다.
- 백엔드는 한국어 평문을 직접 내려주지 않고 `*_user_message_key`만 내려준다.
- 프론트엔드는 이 문서의 key를 기준으로 실제 화면 문구를 표시한다.
- 프롬프트 문구나 에이전트 성격을 직접 바꾸는 문장은 임지빈과 확인한다.
- 프로토콜 상태값, 오류 코드, 종료 사유는 신현성의 `agents/workflows/message_schema.md` 정의를 따른다.

## Key 규칙

| Prefix | 용도 | 예시 |
| --- | --- | --- |
| `screen.*` | 화면 제목과 설명 | `screen.start.title` |
| `input.*` | 입력창 안내 | `input.concern.placeholder` |
| `action.*` | 버튼과 사용자 동작 | `action.start_consultation` |
| `status.*` | 상담 진행 상태 | `status.analyzing` |
| `round.*` | 라운드와 토론 로그 안내 | `round.initial_opinions.title` |
| `final.*` | 최종 결과 화면 라벨 | `final.advice.title` |
| `termination.*` | 강제 종료 또는 조기 종료 안내 | `termination.consensus_reached` |
| `error.*` | 오류와 재시도 안내 | `error.llm_timeout` |

## 화면별 기본 문구

| Key | 표시 위치 | 문구 |
| --- | --- | --- |
| `screen.start.title` | 상담 시작 화면 제목 | 연애 고민을 여러 관점으로 함께 정리해볼게요 |
| `screen.start.description` | 상담 시작 화면 설명 | 지금 상황을 편하게 적어주면 6명의 에이전트가 각자의 관점으로 의견을 나누고, 마지막에 균형 잡힌 조언으로 정리합니다. |
| `input.concern.label` | 고민 입력 라벨 | 고민 내용 |
| `input.concern.placeholder` | 고민 입력 placeholder | 예: 요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어. |
| `input.concern.helper` | 입력 보조 문구 | 관계, 상황, 내가 헷갈리는 지점을 함께 적어주면 더 정확히 정리할 수 있어요. |
| `action.start_consultation` | 시작 버튼 | 상담 시작 |
| `action.retry` | 재시도 버튼 | 다시 시도 |
| `action.edit_question` | 입력 수정 버튼 | 고민 수정 |
| `action.new_consultation` | 새 상담 버튼 | 새 상담 시작 |

## 상담 진행 상태 문구

`ConsultationStatus` 값과 1:1로 맞춘다.

| Status | Key | 짧은 표시 문구 | 보조 문구 |
| --- | --- | --- | --- |
| `pending` | `status.pending` | 상담 준비 중 | 입력한 고민을 상담 흐름에 맞게 준비하고 있어요. |
| `analyzing` | `status.analyzing` | 고민 분석 중 | 관계 상태, 감정, 핵심 이슈를 먼저 정리하고 있어요. |
| `round_1_running` | `status.round_1_running` | 에이전트 의견 모으는 중 | 6명의 에이전트가 각자의 관점에서 첫 의견을 만들고 있어요. |
| `summary_1_running` | `status.summary_1_running` | 쟁점 정리 중 | 나온 의견에서 공통점과 갈리는 지점을 정리하고 있어요. |
| `round_2_running` | `status.round_2_running` | 에이전트 토론 중 | 서로 다른 의견을 비교하며 더 현실적인 조언을 찾고 있어요. |
| `classify_2_running` | `status.classify_2_running` | 토론 흐름 정리 중 | 합의된 부분과 더 볼 필요가 있는 부분을 나누고 있어요. |
| `round_3_running` | `status.round_3_running` | 최종 입장 정리 중 | 각 에이전트가 마지막 입장을 다듬고 있어요. |
| `summarizing` | `status.summarizing` | 결론 작성 중 | 토론 결과를 바탕으로 실행 가능한 조언을 정리하고 있어요. |
| `completed` | `status.completed` | 상담 완료 | 지금 상황에서 가장 균형 잡힌 방향을 정리했어요. |
| `terminated` | `status.terminated` | 상담 정리 완료 | 가능한 범위 안에서 안전하게 상담을 마무리했어요. |
| `failed` | `status.failed` | 상담을 완료하지 못했어요 | 일시적인 문제로 결과를 만들지 못했어요. 잠시 뒤 다시 시도해주세요. |

## 라운드별 화면 문구

| Key | 표시 위치 | 문구 |
| --- | --- | --- |
| `round.initial_opinions.title` | 1라운드 제목 | 첫 의견 |
| `round.initial_opinions.description` | 1라운드 설명 | 에이전트들이 각자의 관점에서 상황을 먼저 해석했어요. |
| `round.discussion.title` | 2라운드 제목 | 토론 과정 |
| `round.discussion.description` | 2라운드 설명 | 서로의 의견을 비교하며 놓친 지점을 보완하고 있어요. |
| `round.final_positions.title` | 3라운드 제목 | 최종 입장 |
| `round.final_positions.description` | 3라운드 설명 | 토론을 반영해 각 에이전트가 마지막 의견을 정리했어요. |
| `round.supervisor_note.title` | 슈퍼바이저 메모 제목 | 정리 메모 |
| `round.skipped_agent` | 스킵된 에이전트 표시 | 이번 라운드에서는 이 에이전트의 의견을 건너뛰었어요. |

## 최종 결과 문구

| Key | 표시 위치 | 문구 |
| --- | --- | --- |
| `final.title` | 최종 결과 화면 제목 | 최종 조언 |
| `final.situation.title` | 상황 정리 섹션 | 상황 정리 |
| `final.disagreements.title` | 쟁점 섹션 | 의견이 갈린 지점 |
| `final.advice.title` | 조언 섹션 | 이렇게 해보면 좋아요 |
| `final.action_items.title` | 액션 아이템 섹션 | 바로 해볼 수 있는 행동 |
| `final.caveats.title` | 주의사항 섹션 | 기억하면 좋은 점 |
| `final.contributing_agents.title` | 참여 에이전트 섹션 | 의견을 낸 에이전트 |
| `final.footer_note` | 결과 하단 안내 | 이 답변은 여러 관점을 정리한 참고용 조언이에요. 중요한 결정은 내 감정과 상황을 함께 보며 천천히 판단해주세요. |

## 최종 주의사항 문구

`final.caveats`에 문구 key가 들어오는 경우 아래 문구로 표시한다.

| Key | 표시 조건 | 문구 |
| --- | --- | --- |
| `final.caveat.safety_refused` | 안전 필터로 상담 범위를 제한한 경우 | 안전한 상담 범위를 벗어난 내용은 자세히 다루지 않았어요. 필요한 경우 신뢰할 수 있는 사람이나 전문가에게 도움을 요청해주세요. |

## 종료 사유 문구

`TerminationReason` 값과 맞춘다. 정상 완료는 보통 `status.completed`와 `final.*` 문구를 사용하고, 조기 종료나 실패 상황에서 아래 key를 사용한다.

| Reason | Key | 사용자 문구 |
| --- | --- | --- |
| `normal` | `termination.normal` | 상담이 정상적으로 완료됐어요. |
| `consensus_reached` | `termination.consensus_reached` | 에이전트들이 충분히 비슷한 결론에 도달해 토론을 일찍 마무리했어요. |
| `repetition_detected` | `termination.repetition_detected` | 같은 의견이 반복되어 핵심 결론을 중심으로 상담을 정리했어요. |
| `round_limit_exceeded` | `termination.round_limit_exceeded` | 정해진 토론 범위 안에서 가능한 결론을 정리했어요. |
| `persona_breakdown` | `termination.persona_breakdown` | 일부 에이전트 의견이 역할 기준에서 벗어나 안전하게 제외하고 상담을 정리했어요. |
| `safety_filter` | `termination.safety_refused` | 이 내용은 안전한 상담 범위를 벗어나 자세한 답변을 제공하기 어려워요. 필요하다면 신뢰할 수 있는 사람이나 전문가에게 도움을 요청해주세요. |
| `timeout` | `termination.timeout` | 상담 시간이 길어져 지금까지 정리된 내용으로 마무리했어요. |
| `internal_error` | `termination.internal_error` | 내부 문제로 상담을 끝까지 진행하지 못했어요. 잠시 뒤 다시 시도해주세요. |

## 오류 문구

`ErrorCode` 값과 맞춘다. 사용자가 원인을 이해하되 기술적 세부사항에 묶이지 않게 쓴다.

| ErrorCode | Key | 사용자 문구 | 권장 동작 |
| --- | --- | --- | --- |
| `LLM_TIMEOUT` | `error.llm_timeout` | 일부 에이전트의 응답이 늦어져 해당 의견을 건너뛰었어요. | 결과 화면에 계속 진행 |
| `LLM_RATE_LIMIT` | `error.llm_rate_limit` | 요청이 잠시 몰려 상담이 지연되고 있어요. 조금 뒤 다시 시도해주세요. | 재시도 버튼 |
| `JSON_PARSE_FAILED` | `error.json_parse_failed` | 일부 응답을 화면에 맞게 정리하지 못해 해당 의견을 제외했어요. | 결과 화면에 계속 진행 |
| `SCHEMA_VIOLATION` | `error.schema_violation` | 일부 응답 형식이 맞지 않아 해당 의견을 제외했어요. | 결과 화면에 계속 진행 |
| `PERSONA_DRIFT` | `error.persona_drift` | 일부 에이전트 의견이 역할 기준과 맞지 않아 제외했어요. | 결과 화면에 계속 진행 |
| `SAFETY_BLOCKED` | `error.safety_blocked` | 안전한 상담 범위를 벗어난 내용이 있어 답변을 제한했어요. | 안내 후 종료 |
| `WORKFLOW_TIMEOUT` | `error.workflow_timeout` | 상담 시간이 너무 길어져 완료하지 못했어요. 잠시 뒤 다시 시도해주세요. | 재시도 버튼 |
| `UNKNOWN` | `error.unknown` | 알 수 없는 문제가 발생했어요. 잠시 뒤 다시 시도해주세요. | 재시도 버튼 |

## 화면 흐름별 표시 순서

1. 시작 화면에서 `screen.start.*`, `input.concern.*`, `action.start_consultation`을 보여준다.
2. 상담 요청 후 `status.*` 문구를 진행 단계에 맞게 바꿔 보여준다.
3. 1라운드는 `round.initial_opinions.*`와 에이전트별 의견 카드를 보여준다.
4. 2라운드는 `round.discussion.*`와 토론 로그를 시간순으로 보여준다.
5. 3라운드는 `round.final_positions.*`와 최종 입장을 보여준다.
6. 결과 화면은 `final.*` 라벨을 기준으로 상황, 쟁점, 조언, 행동 항목, 주의사항을 나눈다.
7. 오류가 있어도 상담이 계속 진행되면 `error.*`를 작은 안내로 보여주고, 전체 실패면 `status.failed`와 `action.retry`를 함께 보여준다.

## 협업 메모

- 김준서: 이 문서의 key를 기준으로 화면 컴포넌트와 라벨 위치를 잡는다.
- 김민우: `PublicTermination.user_message_key`, `PublicError.user_message_key`에는 이 문서의 key만 넣는다.
- 신현성: `ConsultationStatus`, `TerminationReason`, `ErrorCode`가 바뀌면 이 문서도 함께 갱신해야 한다.
- 임지빈: 프롬프트가 사용자에게 직접 보일 수 있는 문장을 만들 경우 이 문서의 말투와 충돌하지 않게 맞춘다.
