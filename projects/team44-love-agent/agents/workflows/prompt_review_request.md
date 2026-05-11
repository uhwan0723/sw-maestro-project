# 프롬프트 리뷰 요청 (jibin/prompts 브랜치)

`agents/prompts/` 폴더의 프롬프트 파일 작성이 완료되었습니다.  
아래 항목을 각 담당자가 확인하고 이상이 있으면 코멘트 또는 수정 요청 바랍니다.

---

## 신현성 확인 사항

### 1. round_prompts.md 라운드별 JSON 필드 ↔ 메시지 스키마 일치 여부

`agents/workflows/message_schema.md` 기준으로 아래 필드명·타입이 맞는지 확인해 주세요.

#### 1라운드 에이전트 출력 (`round1_opinions` 원소)

| 필드명 | 타입 | 설명 |
|---|---|---|
| `agent_name` | string | 에이전트 이름 |
| `stance` | string | 핵심 입장 1문장 |
| `advice` | string | 구체적 조언 |
| `rationale` | string | 근거 |
| `suggested_action` | string | 실행 가능한 행동 1가지 |
| `risk_note` | string | 조언의 주의사항 |

#### 2라운드 에이전트 출력 (`round2_opinions` 원소)

| 필드명 | 타입 | 설명 |
|---|---|---|
| `agent_name` | string | 에이전트 이름 |
| `agrees_with` | string[] | 동의한 에이전트명 목록 |
| `disagrees_with` | string[] | 반박한 에이전트명 목록 |
| `rebuttal` | string | 반박 내용 |
| `supplement` | string | 새로 추가하는 관점/행동 방안 |

#### 3라운드 에이전트 출력 (`round3_opinions` 원소)

| 필드명 | 타입 | 설명 |
|---|---|---|
| `agent_name` | string | 에이전트 이름 |
| `final_stance` | string | 최종 입장 |
| `stance_changed` | boolean | 입장 변경 여부 |
| `change_reason` | string | 변경 이유 (변경 시), 빈 문자열 (유지 시) |
| `final_action` | string | 최종 권고 행동 |

---

### 2. supervisor.md 쟁점 정리 출력 ↔ 슈퍼바이저 개입 규칙 일치 여부

`agents/workflows/supervisor_protocol.md` 기준으로 아래 필드와 규칙이 맞는지 확인해 주세요.

#### 슈퍼바이저 1단계 출력 (1라운드 전)

| 필드명 | 타입 | 설명 |
|---|---|---|
| `situation_brief` | string | 상황 요약 1~2문장 |
| `key_issues` | string[] | 핵심 쟁점 2~3개 |
| `emotional_state` | string | 사용자 감정 상태 |
| `debate_goal` | string | 토론 핵심 질문 1문장 |

이 출력이 라운드 에이전트 입력의 `supervisor_analysis` 키 아래로 전달됩니다.

#### 슈퍼바이저 2단계 출력 (2라운드 전)

| 필드명 | 타입 | 설명 |
|---|---|---|
| `agreements` | string[] | 합의된 내용 (없으면 빈 배열) |
| `conflicts` | string[] | 의견이 갈린 쟁점 |
| `focus_for_round2` | string | 2라운드 집중 질문 |

이 출력이 라운드 2 에이전트 입력의 `supervisor_round2_analysis` 키 아래로 전달됩니다.

> **확인 포인트**: `supervisor_analysis`와 `supervisor_round2_analysis` 키 이름이 프로토콜 문서와 동일한지 확인 필요.

---

## 김민우 확인 사항

### LangGraph 프롬프트 파일 로드 방식

현재 프롬프트는 `agents/prompts/*.md` 파일로 작성되어 있습니다.  
아래 두 방식 중 어떤 방식으로 로드할지 결정 후 알려주세요.

**방식 A — 런타임 파일 로드**
```python
with open("agents/prompts/supervisor.md") as f:
    supervisor_prompt = f.read()
```

**방식 B — 변수 주입 (Python 상수로 분리)**
```python
# agents/prompts/__init__.py 또는 constants.py
SUPERVISOR_ANALYSIS_PROMPT = """..."""
SUPERVISOR_SUMMARY_PROMPT = """..."""
ROUND1_PROMPT = """..."""
```

결정되면 프롬프트 파일 구조 조정이 필요할 수 있습니다.

---

## 박준혁 확인 사항

### final_advice, action_steps 문장 톤 ↔ 프론트 안내 문구 기준

`agents/prompts/final_summary.md`에서 사용자에게 노출되는 주요 텍스트의 톤:

- **`final_advice`**: "감정적 위로와 현실적 조언의 균형", 마지막 문장은 사용자가 스스로 결정하도록 열린 문장으로 끝남
- **`action_steps`**: 사용자 주어로 시작하는 문장 형태 (예: "상대방에게 직접 만나서 이야기하자고 제안해본다")
- **`caution`**: 항상 "이 답변은 전문 심리상담을 대체하지 않습니다" 문구 포함

> 프론트에서 정의된 안내 문구 기준(어조, 경어, 길이 제한 등)과 충돌하는 부분이 있으면 알려주세요.

---

## 김준서 확인 사항

### 프론트 화면에 표시할 필드 목록

각 화면/컴포넌트별로 필요한 필드를 아래에서 선택 후 확인해 주세요.

**최종 결과 화면** (final_summary 출력):
- `situation_summary` — 상황 요약
- `main_conflict` — 에이전트 간 핵심 대립점
- `consensus` — 합의 내용 (null 가능)
- `final_advice` — 최종 조언
- `action_steps` — 실행 단계 목록 (배열)
- `caution` — 주의사항

**라운드별 에이전트 카드** (각 라운드 에이전트 출력):
- `agent_name` — 에이전트 이름
- `stance` — 핵심 입장
- `advice` — 조언 (1라운드)
- `suggested_action` — 권고 행동 (1라운드)
- `final_action` — 최종 권고 행동 (3라운드)

**슈퍼바이저 분석 표시** (필요 시):
- `situation_brief` — 상황 요약
- `key_issues` — 핵심 쟁점 태그
- `debate_goal` — 토론 목표

> 표시 여부, 필드명 변경 필요, 추가로 필요한 필드가 있으면 알려주세요.

---

## 파일 위치 참고

```
agents/prompts/
├── supervisor.md          # 슈퍼바이저 1단계·2단계 프롬프트
├── relationship_agents.md # 6개 에이전트 시스템 프롬프트
├── round_prompts.md       # 1·2·3라운드 공통 지시문
└── final_summary.md       # 최종 통합 요약 프롬프트
```
