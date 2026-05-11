# 01. 시스템 아키텍처

## 1. 컴포넌트 구성도

```
┌─────────────────┐
│ Frontend (Next.js, App Router) │  티어/스타일/질문 입력 · 결과 카드 · 출처 · 확신도
└────────┬────────┘
         │ HTTPS / JSON
         ▼
┌────────────────────────────────────────────────┐
│ Backend API Gateway (FastAPI)                  │
│  - Pydantic 검증 / request_id 발급             │
│  - L1 LRU + L2 SQLite 캐시 (patch-keyed)       │
│  - Rate limit / Timeout / Semaphore(8)         │
│  - LangGraph Strategy Agent 호출               │
└──┬─────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────┐
│ DeckGuru Strategy Agent (LangGraph StateGraph)         │
│                                                        │
│  ┌──────────────┐                                      │
│  │analyze_intent│ — LLM(small, T=0)                    │
│  └──────┬───────┘                                      │
│         ▼                                              │
│  ┌──────────────┐                                      │
│  │rag_retrieve  │ — RAG Service                        │
│  │(units/items/ │                                      │
│  │ traits/augs/ │                                      │
│  │ decks/...)   │                                      │
│  └──────┬───────┘                                      │
│         ▼                                              │
│  ┌──────────────┐   conditional                        │
│  │need_live?    ├─── yes ──► [Live Research Sub-graph] │
│  │(rag_score<θ  │                  ReAct (max 5 steps) │
│  │ or freshness)│            ◀── facts + sources       │
│  └──────┬───────┘                                      │
│         ▼ no                                           │
│  ┌──────────────┐                                      │
│  │analyze_meta  │ — LLM (T=0, structured)              │
│  └──────┬───────┘                                      │
│         ▼                                              │
│  ┌──────────────┐                                      │
│  │recommend     │ — LLM (T=0, structured)              │
│  └──────┬───────┘                                      │
│         ▼                                              │
│  ┌──────────────┐                                      │
│  │verify_       │ — Pure function                      │
│  │grounding     │   (whitelist / numeric / sources)    │
│  └──────┬───────┘                                      │
│         ▼                                              │
│  ┌──────────────┐                                      │
│  │format_       │ — Pure function (Pydantic)           │
│  │response      │                                      │
│  └──────┬───────┘                                      │
└─────────┼──────────────────────────────────────────────┘
          ▼
┌──────────────────────────┐  ┌────────────────────────┐
│ RAG Service              │  │ Live Research          │
│ - ChromaDB (8 indices)   │  │ - web_search (Tavily)  │
│ - patch_version filter   │  │ - fetch_page (Trafil.) │
│ - hybrid (BM25 + dense)  │  │ - youtube_transcript   │
│ - whitelist API          │  │ - extract_facts (LLM)  │
└──────────────────────────┘  └────────────────────────┘
          │                            │
          ▼                            ▼
┌──────────────────────────┐  ┌────────────────────────┐
│ Vector DB (ChromaDB)     │  │ Domain Whitelist       │
│ - 8 collections          │  │ - lolchess.gg, MetaTFT │
│ - patch_version metadata │  │ - 공식 패치 노트       │
└──────────────────────────┘  │ - 사전 합의된 YT 채널  │
                              └────────────────────────┘
```

## 2. 요청 흐름 (Sequence)

```
User → Frontend → Backend
  1. POST /api/recommend (tier, play_style, question)
     → Pydantic 검증, request_id 발급, 캐시 lookup (key = sha256(tier|style|norm(q)|patch))
     → cache miss 시 Strategy Agent 호출 (asyncio.wait_for, timeout=25s)
  2. Agent: analyze_intent
     → intent ∈ {recommend_deck, deck_playstyle, item_pivot, patch_summary, other}
     → other이면 short-circuit → format_response 직행
  3. Agent: rag_retrieve
     → 인텐트별 query plan으로 8개 인덱스 중 관련 인덱스 검색
     → patch_version 필터 강제
  4. Agent: need_live? (조건부)
     → trigger 조건: avg_rag_score < 0.4 OR question에 "이번 패치"/"오늘"/"최근" 키워드
     → trigger 시 Live Research sub-graph (ReAct, 최대 5 step)
  5. Agent: analyze_meta → recommend → verify_grounding → format_response
  6. Backend: 응답 정규화 → L1+L2 캐시 저장 → Frontend 반환
```

LLM 호출 수: **최소 2회** (intent + recommend) / **평균 3~4회** (+ analyze_meta) / **최대 8회** (+ Live Research ReAct).

## 3. Agent 분담 원칙

| 역할 | Agentic 패턴 | LLM 사용 | 결정성 |
|---|---|---|---|
| Strategy Agent | LangGraph 순차 노드 (intent → retrieve → meta → recommend → verify → format). need_live 조건부 분기. | LLM 2~4회 (T=0, structured) | 검증/포맷은 100% 결정적, LLM은 schema 강제 |
| RAG Service | 결정적 검색 (BM25 + dense hybrid) + patch 필터 + whitelist API. LLM 미사용. | 0회 | 100% 결정적 |
| Live Research | ReAct 루프 (최대 5 step). 도구 화이트리스트(웹검색/페이지/유튜브 자막). LLM이 fact extraction. | LLM 1~3회 | 부분 결정성 (다중 소스 합의 + schema) |

## 3.1 LangGraph 채택 (전역)

본 프로젝트의 Strategy Agent와 Live Research Sub-graph는 모두 **LangGraph StateGraph**로 구현한다.

| 계층 | LangGraph 역할 |
|---|---|
| Strategy Agent | super-graph (StateGraph). 노드 = 결정적 함수 또는 LLM 호출. |
| Live Research | sub-graph. 본인 ReAct 루프 (Action → Observation → Thought) 최대 5 step. |
| 관측성 | LangSmith trace 통합 (선택). 노드별 latency / token / 입출력 자동 기록. |

### State 정의 (Pydantic)

```python
class StrategyState(BaseModel):
    # 입력
    request_id: str
    tier: Tier
    play_style: PlayStyle
    question: str

    # 분류
    intent: Intent | None = None

    # RAG 결과
    rag_chunks: list[RagChunk] = []
    rag_avg_score: float = 0.0

    # Live Research (조건부)
    web_facts: list[WebFact] = []
    research_steps: int = 0

    # 합성
    meta_summary: str | None = None
    candidate_decks: list[DeckDraft] = []
    final_decks: list[DeckRecommendation] = []

    # 검증/메타
    sources: list[Source] = []
    confidence: Confidence = "medium"
    warnings: list[str] = []
    errors: list[str] = []
    patch_version: str
```

State는 `07-data-contracts.md`의 schema와 1:1 일치.

### 결정적 보장

- LangGraph 자체는 결정성을 깨지 않는다. 노드는 순수 함수 또는 LLM(`T=0`).
- `verify_grounding`, `format_response`는 LLM 미사용 — 항상 동일 결과.
- LLM 호출 노드는 schema 검증 실패 시 1회 retry → 그래도 실패하면 fallback (rule-based template).

### Checkpoint

- LangGraph의 in-memory checkpointer를 활성화 → 노드별 state 스냅샷 저장.
- 재현 테스트: 동일 input + 동일 RAG state → 동일 final state assertion.

### Super-graph 흐름

```
[START]
   │
   ▼
[analyze_intent] ── intent=other ─────────────────┐
   │                                              │
   ▼                                              │
[rag_retrieve]                                    │
   │                                              │
   ▼                                              │
[need_live?] ── yes ──► [live_research_subgraph]  │
   │                            │                 │
   │ no                         │                 │
   ▼                            ▼                 │
[analyze_meta] ◄────────── (join)                 │
   │                                              │
   ▼                                              │
[recommend]                                       │
   │                                              │
   ▼                                              │
[verify_grounding]                                │
   │                                              │
   ▼                                              │
[format_response] ◄───────────────────────────────┘
   │
   ▼
[END]
```

조건부 엣지: `need_live?` 노드 결과로 분기. `analyze_intent`에서 `intent=other` 감지 시 직접 `format_response`로 점프.

## 4. 디렉토리 레이아웃

```
ai-swm-51/
├── docs/specs/                       # 본 spec 디렉토리
├── frontend/                         # Next.js (Frontend 담당)
│   ├── src/{app,components,lib}
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/                      # FastAPI 라우터 (Backend 담당)
│   │   ├── agents/
│   │   │   └── strategy/             # Strategy Agent (Agent담당 1)
│   │   ├── rag/                      # RAG Service (Agent담당 2)
│   │   │   ├── ingest.py
│   │   │   ├── index.py
│   │   │   ├── search.py
│   │   │   └── whitelist.py
│   │   ├── research/                 # Live Research (Agent담당 3)
│   │   │   ├── graph.py              # ReAct sub-graph
│   │   │   ├── tools/
│   │   │   │   ├── web_search.py
│   │   │   │   ├── fetch_page.py
│   │   │   │   └── youtube_transcript.py
│   │   │   └── extract_facts.py
│   │   ├── schemas/                  # Pydantic (07-data-contracts 기준)
│   │   ├── services/
│   │   │   ├── cache.py
│   │   │   └── feedback_store.py
│   │   └── settings.py
│   ├── data/
│   │   ├── chroma/                   # ChromaDB persistent dir
│   │   ├── raw/                      # 크롤링 원본
│   │   └── processed/                # chunked JSONL
│   ├── scripts/
│   │   └── build_rag.py
│   ├── tests/
│   │   ├── fixtures/                 # 골든 입력 + 기대 응답
│   │   ├── test_strategy.py
│   │   ├── test_rag.py
│   │   ├── test_research.py
│   │   └── test_e2e.py
│   ├── evals/
│   │   ├── golden_set.jsonl
│   │   └── run_evals.py
│   └── pyproject.toml
└── README.md
```

## 5. 데이터 흐름 보장

### 5.1 멱등성

- `request_id` 단위로 모든 중간 산출물(intent / rag_chunks / web_facts / final_decks)을 캐시한다.
- 동일 `request_id` 재요청 시 LLM 재호출 없이 캐시 결과 반환.
- 캐시 키는 `sha256(tier|play_style|normalize(question)|patch_version)`. patch가 바뀌면 자동 무효화.

### 5.2 실패 처리

| 단계 | 실패 유형 | 대응 |
|---|---|---|
| 입력 검증 | tier/style/question 위반 | 400 `validation_error` |
| analyze_intent | LLM 응답이 enum 외 | 1회 retry → fallback `other` |
| rag_retrieve | ChromaDB error | 502 `rag_unavailable` |
| need_live | trigger됐는데 도메인 화이트리스트 위반 | warning + Live Research skip |
| Live Research | 5 step 초과 / latency > 15s | 부분 결과 + warning `research_truncated` |
| Live Research | 단일 소스만 / extraction conf < 0.5 | confidence 강등 + warning |
| recommend | LLM schema fail 2회 연속 | 502 `agent_failed` |
| verify_grounding | final_decks가 0개로 줄어듦 | confidence=low + warning `all_decks_filtered` |
| 전체 timeout | 25s 초과 | 504 `agent_timeout` |

### 5.3 관측성 (Observability)

- 모든 Agent 호출은 다음을 로깅:
  - `request_id`, `node_name`, `latency_ms`, `tokens_in/out`, `schema_pass`, `intent`, `confidence`
- LLM 호출은 raw response를 7일간 보관 (디버깅 + 회귀 골든셋 후보).
- Live Research 트리거 시 `react_steps`, `sources_count`, `domains_visited[]` 추가 기록.

## 6. 보안 / 프라이버시

- 사용자 입력에 PII 없음 (티어/스타일/질문만). 로그 안전.
- LLM API 키는 Backend env에만 존재. Frontend에서 절대 접근 불가.
- 외부 도메인 fetch는 화이트리스트(`04-agent-research-spec.md` §7) 외 차단.
- 크롤링은 robots.txt + ToS 사전 검토. 1 req / N s rate limit 강제.

## 7. 비-목표 (시스템 차원)

- 다중 사용자 인증/권한 (MVP는 익명 단일 세션)
- 학습/파인튜닝 (모든 추론은 zero-shot + RAG)
- 실시간 스트리밍 (단일 요청-응답). 진행 상태는 Frontend 측 progressive label로 시뮬레이션.
- 멀티턴 대화 메모리 (단발 추천만)
