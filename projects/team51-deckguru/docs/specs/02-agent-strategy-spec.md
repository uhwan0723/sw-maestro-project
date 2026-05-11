# 02. Strategy Agent — LangGraph 오케스트레이션

> 담당: Agent 1 (Strategy / Orchestration)
> 범위: LangGraph StateGraph, 노드별 LLM 프롬프트, intent 분류, 메타 합성, 추천 생성, grounding 검증, 응답 포맷팅
> 의존:
> - `03-agent-rag-spec.md` (RAG Service 호출 인터페이스)
> - `04-agent-research-spec.md` (Live Research sub-graph 호출)
> - `07-data-contracts.md` (StrategyState / RecommendationResponse)

---

## 1. 책임 범위

| 포함 | 제외 |
|---|---|
| LangGraph StateGraph 정의 (노드/엣지/조건부 분기) | RAG 인덱싱 (Agent2) |
| 시스템/유저 프롬프트 작성 + 버전 관리 | 외부 웹 크롤링 (Agent3) |
| intent 분류 + few-shot | HTTP 라우팅 (Backend) |
| structured output 강제 + retry | UI 렌더링 (Frontend) |
| `verify_grounding` 결정적 로직 | 평가 지표 자동 측정 (공동) |
| `format_response` Pydantic 매핑 | |

---

## 2. State 정의

`01-architecture.md` §3.1 참조. Pydantic v2 모델로 구현. `07-data-contracts.md`의 `StrategyState` schema와 1:1 일치.

```python
# backend/app/agents/strategy/state.py
from pydantic import BaseModel, Field
from app.schemas.shared import (
    Tier, PlayStyle, Intent, Confidence,
    RagChunk, WebFact, Source, DeckDraft, DeckRecommendation,
)

class StrategyState(BaseModel):
    request_id: str
    patch_version: str

    # input
    tier: Tier
    play_style: PlayStyle
    question: str

    # intent
    intent: Intent | None = None

    # retrieval
    rag_chunks: list[RagChunk] = Field(default_factory=list)
    rag_avg_score: float = 0.0

    # live research (optional)
    need_live: bool = False
    web_facts: list[WebFact] = Field(default_factory=list)
    research_steps: int = 0

    # synthesis
    meta_summary: str | None = None
    candidate_decks: list[DeckDraft] = Field(default_factory=list)
    final_decks: list[DeckRecommendation] = Field(default_factory=list)

    # meta
    sources: list[Source] = Field(default_factory=list)
    confidence: Confidence = "medium"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
```

---

## 3. 노드별 명세

### 3.1 `analyze_intent`

| 항목 | 내용 |
|---|---|
| 입력 | `tier`, `play_style`, `question` |
| 출력 | `intent` (enum), `warnings` (필요 시) |
| LLM | yes (small/cheap, T=0, structured output) |
| 실패 정책 | enum 외 응답 → 1회 retry → `intent=other` fallback |

**Few-shot examples (`prompts/intents.json`):**
```json
[
  {"q": "현재 패치에서 골드가 티어 올리기 좋은 덱 3개 추천해줘", "intent": "recommend_deck"},
  {"q": "요즘 많이 나오는 덱 하나 골라서 초반부터 후반까지 운영법 알려줘", "intent": "deck_playstyle"},
  {"q": "초반에 곡궁이 많이 나왔는데 어떤 덱 가면 좋아?", "intent": "item_pivot"},
  {"q": "이번 롤토체스 패치에서 메타에 영향 큰 변경점만 알려줘", "intent": "patch_summary"},
  {"q": "롤토체스 게임 처음 깔았는데 회원가입 어떻게 해?", "intent": "other"}
]
```

**Structured output schema:**
```json
{"type":"object","required":["intent"],"properties":{
  "intent":{"enum":["recommend_deck","deck_playstyle","item_pivot","patch_summary","other"]},
  "extracted_keywords":{"type":"array","items":{"type":"string"}}
}}
```

### 3.2 `rag_retrieve`

| 항목 | 내용 |
|---|---|
| 입력 | `intent`, `tier`, `play_style`, `question`, `extracted_keywords` |
| 출력 | `rag_chunks: list[RagChunk]`, `rag_avg_score: float` |
| LLM | no (RAG Service 호출만) |

**Query plan per intent:**

| intent | 검색 인덱스 | k | 추가 필터 |
|---|---|---|---|
| recommend_deck | deck_templates, augments, traits | 5+3+3 | difficulty 가중 (style 의존) |
| deck_playstyle | deck_templates, playbook, units | 1+5+3 | extracted_keywords로 deck name 매칭 |
| item_pivot | items, deck_templates, units | 5+3+3 | item 화이트리스트 우선 매칭 |
| patch_summary | patch_summary, deck_templates | 8+3 | patch_version=current만 |
| other | (skip) | - | - |

모든 검색에 `where={"patch_version": current_patch}` 필터 강제.

`rag_avg_score`는 top-3 chunk의 cosine similarity 평균.

### 3.3 `need_live?` (조건부 엣지)

순수 함수, LLM 미사용.

```python
def need_live(state: StrategyState) -> bool:
    if state.intent == "other":
        return False
    if state.rag_avg_score < 0.4:
        return True  # RAG가 충분히 매칭하지 못함
    if any(k in state.question for k in ["이번 패치", "오늘", "최근", "어제"]):
        return True  # freshness 키워드
    if state.intent == "patch_summary" and patch_age_days(state.patch_version) <= 3:
        return True  # 패치 직후 정보 부족 가능성
    return False
```

### 3.4 `live_research` (sub-graph 호출)

`04-agent-research-spec.md`의 sub-graph를 호출. 입력: `state.question + state.extracted_keywords`. 출력: `web_facts`, `sources`, `research_steps`.

타임아웃 15s. 초과 시 부분 결과 + warning.

### 3.5 `analyze_meta`

| 항목 | 내용 |
|---|---|
| 입력 | `rag_chunks`, `web_facts` |
| 출력 | `meta_summary: str (≤300자)`, `candidate_decks: list[DeckDraft] (≤5)` |
| LLM | yes (T=0, structured) |

**시스템 프롬프트 핵심:**
- "현재 패치 메타를 한 단락으로 요약하라."
- "강세 덱 후보를 RAG/web_facts에 등장한 것 중에서만 추출하라. 새로운 덱을 만들어내지 말 것."
- "각 후보에 대해 RAG/web_facts의 어느 사실이 근거인지 `evidence_chunk_ids[]`로 표기."

### 3.6 `recommend`

| 항목 | 내용 |
|---|---|
| 입력 | `tier`, `play_style`, `intent`, `meta_summary`, `candidate_decks`, `rag_chunks`, `web_facts` |
| 출력 | `final_decks: list[DeckRecommendation] (≤3)` |
| LLM | yes (T=0, structured) |

**시스템 프롬프트 핵심 (요약):**
```
당신은 롤토체스 전략 코치 "DeckGuru"입니다.

[원칙]
- 사실 근거 우선: 응답에 등장하는 모든 기물/아이템/특성/증강체는 컨텍스트(RAG/web_facts)에 존재해야 한다. 컨텍스트에 없으면 절대 만들어내지 말 것.
- 패치 정합성: 응답은 patch_version={patch} 기준이어야 한다. 이전 패치 정보 인용 금지.
- 사용자 조건 우선: tier={tier}, play_style={style}에 맞는 덱만 추천하라.
  - easy_beginner → difficulty=easy 우선
  - high_risk_first → 1위 빈도가 높은 덱 우선 (web_facts에 있을 때만)
  - stable_top4 → 평균 등수가 좋은 덱 우선
- 보장 금지: "1등 보장", "승률 100%", "무조건" 등 단정 표현 금지.
- 출처 의무: rationale에 인용한 사실은 sources[] 항목과 1:1 대응.
- intent별 응답 형식:
  - recommend_deck: 2~3개 덱
  - deck_playstyle: 1개 덱 + 상세 phase별 운영
  - item_pivot: 1~3개 덱 (해당 아이템과 시너지)
  - patch_summary: meta_summary 비중 높이고 decks는 최대 2개

[톤앤매너]
- 초보자도 이해 가능한 언어. 어려운 용어는 풀어서 설명.
- 단정 대신 "현재 자료 기준 강세" 같은 표현.
```

**Structured output:** `RecommendationResponse`의 `decks[]` 부분.

### 3.7 `verify_grounding` (결정적, LLM 미사용)

```python
def verify_grounding(state: StrategyState) -> StrategyState:
    whitelist = rag_service.get_whitelist(state.patch_version)
    # whitelist = {"units": {...}, "items": {...}, "traits": {...}, "augments": {...}}

    filtered_decks = []
    for deck in state.final_decks:
        # 1. 화이트리스트 매칭
        deck.core_units = [u for u in deck.core_units if u in whitelist["units"]]
        deck.key_items = [i for i in deck.key_items if i in whitelist["items"]]

        # 2. 빈 deck 제거
        if len(deck.core_units) < 3:
            state.warnings.append(f"deck_filtered_{deck.name}_insufficient_units")
            continue

        # 3. rationale 수치 필터
        deck.rationale = filter_unsourced_numbers(deck.rationale, state.web_facts)

        # 4. 금지 표현 제거
        deck.rationale = sanitize_forbidden_phrases(deck.rationale)

        filtered_decks.append(deck)

    state.final_decks = filtered_decks

    # 5. confidence 산출
    if len(filtered_decks) == 0:
        state.confidence = "low"
        state.warnings.append("all_decks_filtered")
    elif state.rag_avg_score >= 0.6 and len(state.sources) >= 1:
        state.confidence = "high"
    else:
        state.confidence = "medium"

    return state
```

**금지 표현 정규식:**
```
\b(1등 보장|승률 100%?|무조건|확실히|반드시 1등)\b
```

**수치 필터:** rationale 내 `\d+(\.\d+)?%?` 매칭 → `web_facts[].quote` 또는 `rag_chunks[].text`에 동일 수치가 없으면 정성 표현으로 변환 ("높은 편" / "낮은 편" / 제거).

### 3.8 `format_response` (결정적)

`RecommendationResponse` Pydantic 모델로 매핑. `request_id`, `patch_version`, `generated_at` 채움. JSON serialize.

---

## 4. 프롬프트 버전 관리

`backend/app/agents/strategy/prompts/`:
```
prompts/
├── system_recommend.v1.txt
├── system_meta.v1.txt
├── intents.v1.json          # few-shot
└── manifest.yaml            # 활성 버전 명시
```

`manifest.yaml`:
```yaml
active:
  intent: v1
  meta: v1
  recommend: v1
```

프롬프트 변경 시 새 버전 파일 추가 + manifest 갱신. 활성 버전은 응답에 포함하지 않지만 로깅은 함.

---

## 5. 인터페이스 — Backend 호출 계약

```python
# backend/app/agents/strategy/api.py
from app.schemas.api import RecommendationResponse

async def run_strategy_agent(
    request_id: str,
    tier: Tier,
    play_style: PlayStyle,
    question: str,
    *,
    patch_version: str,
    timeout_s: float = 25.0,
) -> RecommendationResponse:
    """단일 진입점. Backend는 이 함수만 호출."""
```

타임아웃 초과 → `RecommendationTimeout` 예외. Backend는 504로 매핑.

---

## 6. 결정성 / 재현성

| 단계 | 결정성 | 보장 방법 |
|---|---|---|
| analyze_intent | LLM | T=0, structured, retry 1회. 같은 prompt → 같은 응답 (동일 모델 가정). |
| rag_retrieve | 100% | 순수 함수. 동일 RAG state → 동일 결과. |
| need_live | 100% | 순수 함수. |
| live_research | 부분 | 외부 시점성 — 동일 시점에는 결정적. 7일 raw 캐시로 재현. |
| analyze_meta / recommend | LLM | T=0, structured, retry 1회. |
| verify_grounding / format | 100% | 순수 함수. |

**재현 테스트:**
```python
# tests/test_strategy_repro.py
def test_same_input_same_output(mock_llm, fixed_rag):
    s1 = run_strategy_agent_sync(...)
    s2 = run_strategy_agent_sync(...)
    assert s1.dict() == s2.dict()
```

---

## 7. 디렉토리 구조

```
backend/app/agents/strategy/
├── __init__.py
├── api.py                   # run_strategy_agent 단일 진입점
├── state.py                 # Pydantic StrategyState
├── graph.py                 # LangGraph StateGraph 정의
├── nodes/
│   ├── analyze_intent.py
│   ├── rag_retrieve.py
│   ├── need_live.py
│   ├── analyze_meta.py
│   ├── recommend.py
│   ├── verify_grounding.py
│   └── format_response.py
├── prompts/
│   ├── system_recommend.v1.txt
│   ├── system_meta.v1.txt
│   ├── intents.v1.json
│   └── manifest.yaml
└── llm.py                   # LLM client wrapper (T=0, structured, retry)
```

---

## 8. 평가

`evals/golden_set.jsonl` 20문항. Strategy Agent에 책임 있는 지표:

| 지표 | 목표 |
|---|---|
| Intent Accuracy | ≥ 90% |
| Schema Pass Rate | ≥ 98% |
| Grounding Pass Rate (whitelist 매칭) | ≥ 95% |
| Confidence 일관성 (high에서 sources≥1) | 100% |

CI: 매 PR마다 `python -m evals.run_evals`.

---

## 9. 기획서 피드백

| # | 기획서 | 문제 | 본 spec 보정 |
|---|---|---|---|
| 1 | "싱글 에이전트가 순차로 작업"(§2.2) | 진짜 싱글 에이전트인지 워크플로우인지 모호 | LangGraph StateGraph로 명시. 외부 명칭만 "Agent" 유지 |
| 2 | 환각 방지 = "RAG 활용"(§1.4) | RAG는 환각 *감소*에 그침 | §3.7에 화이트리스트/수치/금지 표현 다층 필터 |
| 3 | "정보 수집 → RAG 검색 → 메타 분석 → 추천"의 무조건 순차 | freshness 트리거 없음 | §3.3 `need_live?` 조건부 분기로 ReAct 활성화 |
| 4 | LLM 모델 미명시 | 비용/일정 영향 큼 | §4 prompt manifest로 모델 추상화. 4/29 합의 |
| 5 | "확신도 높음/중간/낮음"(§5.1) | 산출 룰 없음 | §3.7에 결정적 룰 (rag_score + sources count) |
| 6 | rationale에 수치 등장 가능 | 환각 위험 | §3.7 수치 필터 |
| 7 | intent 분류 부재 | 모든 질문을 동일 처리 | §3.1 4개 인텐트 + few-shot + structured |
