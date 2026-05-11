# DeckGuru Backend

TFT 덱 추천 AI 서비스의 FastAPI 게이트웨이.  
Strategy Agent 호출 · 캐싱 · Rate Limit · 로깅을 담당합니다.

---

## 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [디렉토리 구조](#디렉토리-구조)
3. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
4. [환경 변수](#환경-변수)
5. [API 엔드포인트](#api-엔드포인트)
6. [요청 흐름](#요청-흐름)
7. [캐시 구조](#캐시-구조)
8. [테스트 실행](#테스트-실행)
9. [팀원 연동 가이드](#팀원-연동-가이드)
10. [Docker](#docker)

---

## 아키텍처 개요

```
Frontend (Next.js)
    │ POST /api/recommend
    ▼
Backend (FastAPI, :8000)        ← 이 서비스
    │ run_strategy_agent()
    ▼
Strategy Agent (LangGraph)      ← Agent-1 담당
    │ RagService.search()
    ▼
RAG Service (ChromaDB)          ← Agent-2 담당
```

Backend는 **오케스트레이션을 하지 않습니다.**  
`run_strategy_agent()` 한 번 호출 후 결과를 캐싱·반환하는 게 전부입니다.

---

## 디렉토리 구조

```
backend/
├── app/
│   ├── main.py                  # FastAPI 앱 조립, 미들웨어, 라우터 등록
│   ├── settings.py              # pydantic-settings (.env 로드, 누락 시 startup 실패)
│   ├── api/
│   │   ├── recommend.py         # POST /api/recommend — 메인 추천 엔드포인트
│   │   ├── health.py            # GET  /api/health
│   │   ├── patch_info.py        # GET  /api/patch-info
│   │   ├── feedback.py          # POST /api/feedback
│   │   ├── examples.py          # GET  /api/example-questions
│   │   └── internal.py          # GET  /api/_internal/cache-stats (관리자)
│   ├── middleware/
│   │   ├── request_id.py        # X-Request-ID 헤더 발급 (uuid4)
│   │   └── logging_mw.py        # structlog JSON 로깅 (request_start / request_done)
│   ├── schemas/
│   │   ├── enums.py             # Tier, PlayStyle, Intent, Confidence 등
│   │   ├── shared.py            # DeckRecommendation, Source, PlaybookStep 등
│   │   └── api.py               # RecommendRequest, RecommendationResponse, FeedbackRequest
│   └── services/
│       ├── normalize.py         # normalize_question(), cache_key() — 캐시 키 생성
│       ├── cache.py             # L1 LRU (in-memory) + L2 SQLite 캐시
│       ├── feedback_store.py    # SQLite feedback 테이블 저장
│       ├── limiter.py           # slowapi Limiter 싱글턴
│       └── strategy_invoker.py  # run_strategy_agent() — Strategy Agent 호출 경계
├── scripts/
│   ├── build_rag.py             # processed JSONL → ChromaDB 빌드/갱신
│   └── manual_live_research.py  # Live Research 수동 점검
├── tests/
│   ├── conftest.py              # AsyncClient fixture (임시 DB, Agent monkeypatch)
│   ├── fixtures/mock_responses/
│   │   └── recommend_deck_gold_stable.json  # 명시적 mock fixture
│   ├── test_recommend.py        # /api/recommend 통합 테스트
│   ├── test_cache.py            # 캐시 키 정규화 단위 테스트
│   └── test_health.py           # /api/health, /api/patch-info, /api/example-questions
├── .env.example                 # 환경 변수 샘플
├── pyproject.toml
└── Dockerfile
```

---

## 로컬 개발 환경 설정

### 요구 사항

- Python 3.11 이상
- pip 또는 [uv](https://github.com/astral-sh/uv)

### 설치

```bash
cd backend

# pip 사용 시
pip install -e ".[backend,dev,rag]"

# uv 사용 시 (권장)
uv sync
```

### 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집 — 최소한 PATCH_VERSION 확인
```

### RAG 인덱스 빌드

`/api/recommend` 기본 경로는 Chroma-backed RAG를 사용합니다. 로컬 Chroma 산출물이 없으면 `/api/recommend`는 `502 rag_unavailable`을 반환할 수 있습니다.

처음 로컬에서 빌드할 때는 BGE-M3 임베딩 모델이 필요합니다. 네트워크가 불안정하면 모델을 먼저 로컬 디렉토리에 내려받은 뒤 `EMBEDDING_MODEL`로 경로를 지정합니다.

```bash
cd /Users/dongwoo/Projects/deckguru/backend
.venv/bin/python -m pip install -e ".[backend,dev,rag]"

mkdir -p ../models
.venv/bin/hf download BAAI/bge-m3 --local-dir ../models/bge-m3
```

다운로드 후에는 전체 모델 디렉토리를 `EMBEDDING_MODEL`에 지정하고 Chroma 인덱스를 빌드합니다.

```bash
cd /Users/dongwoo/Projects/deckguru
EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  backend/.venv/bin/python -m backend.scripts.build_rag build --patch 17.2
```

빌드가 끝나면 backend를 같은 모델 경로로 실행합니다.

```bash
cd /Users/dongwoo/Projects/deckguru/backend
EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  uvicorn app.main:app --reload --port 8000
```

### 서버 실행

```bash
uvicorn app.main:app --reload --port 8000
```

실행 확인:

```bash
curl http://localhost:8000/api/health
```

### Swagger UI

서버 실행 후 브라우저에서:

```
http://localhost:8000/docs
```

---

## 환경 변수

`.env.example` 파일을 `.env`로 복사 후 편집합니다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APP_ENV` | `local` | `local` / `staging` / `production` |
| `PATCH_VERSION` | `17.2` | **현재 패치 버전** — RAG 검색 필터에 사용 |
| `CHROMA_PATH` | `../data/rag/vectorstore/chroma` | ChromaDB 경로 (Agent-2 빌드 결과물) |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | BGE-M3 모델명 또는 로컬 모델 디렉토리 |
| `RAG_MIN_SCORE` | `0.05` | RAG chunk 유사도 최소 점수 |
| `UPSTAGE_API_KEY` | _(없음)_ | Strategy Agent LLM 호출에 필요한 Upstage API 키 |
| `UPSTAGE_MODEL_RECOMMEND` | `solar-pro2` | 추천 생성 모델 |
| `UPSTAGE_MODEL_META` | `solar-pro2` | 메타 요약 모델 |
| `UPSTAGE_MODEL_INTENT` | `solar-mini` | 의도 분류 모델 |
| `LIVE_RESEARCH_ENABLED` | `true` | 최신성 보강용 Live Research 사용 여부 |
| `LIVE_RESEARCH_TIMEOUT_S` | `12` | Live Research가 검색/fetch까지 수행할 수 있도록 배정한 초 단위 예산 |
| `LIVE_RESEARCH_MAX_STEPS` | `2` | Live Research에서 실행할 최대 검색/페이지 확인 단계 수 |
| `RESEARCH_LLM_PLANNER_ENABLED` | `false` | `true` 시 검색 계획을 LLM structured output으로 생성 |
| `RESEARCH_LLM_EXTRACT_ENABLED` | `false` | `true` 시 fact 추출을 LLM structured output으로 생성 |
| `AGENT_TIMEOUT_S` | `40` | `/api/recommend` 전체 Strategy Agent timeout |
| `ADMIN_TOKEN` | `dev-admin` | `/api/_internal/cache-stats` 접근 토큰 |
| `DEMO_MODE` | `false` | `true` 시 Rate Limit 완화 (100/min) |
| `MOCK_STRATEGY_AGENT` | `false` | `true`일 때만 fixture 기반 추천 응답 사용 |
| `TAVILY_API_KEY` | _(없음)_ | Live Research용 API 키 |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `APP_LOG_FORMAT` | `console` | `console`이면 로컬 개발용 pretty 로그, `json`이면 JSON 로그 |
| `APP_LOG_COLORS` | `true` | 콘솔 로그 ANSI color 사용 여부 |

---

## API 엔드포인트

전체 명세는 서버 실행 후 `/docs` 참조.

### `POST /api/recommend` — 덱 추천 (메인)

**Request:**
```json
{
  "tier": "GOLD",
  "play_style": "stable_top4",
  "question": "현재 패치에서 골드가 티어 올리기 좋은 덱 추천해줘"
}
```

`tier` 가능 값: `IRON` `BRONZE` `SILVER` `GOLD` `PLATINUM` `EMERALD` `DIAMOND` `MASTER+`  
`play_style` 가능 값: `stable_top4` `high_risk_first` `easy_beginner` `flexible`  
`question`: 1~500자 자유 입력

**Response Headers:**
```
X-Request-ID: <uuid>
X-Cache: HIT | MISS
X-Patch-Version: 17.2
```

**Response Body:** `RecommendationResponse`
```json
{
  "request_id": "...",
  "patch_version": "17.2",
  "intent": "recommend_deck",
  "meta_summary": "현재 메타 요약...",
  "decks": [
    {
      "name": "마스터 이 킨드레드",
      "difficulty": "medium",
      "core_units": ["마스터 이", "킨드레드", "..."],
      "key_items": ["밤의 끝자락", "..."],
      "augment_direction": "사냥꾼 상징 우선",
      "playbook": [
        {"phase": "early", "instruction": "..."},
        {"phase": "mid",   "instruction": "..."},
        {"phase": "late",  "instruction": "..."}
      ],
      "good_conditions": ["..."],
      "avoid_conditions": ["..."],
      "fallback_plan": "...",
      "rationale": "..."
    }
  ],
  "sources": [
    {
      "title": "Lolchess 메타 덱 랭킹",
      "url": "https://lolchess.gg/...",
      "snippet": "...",
      "source_kind": "meta_site"
    }
  ],
  "confidence": "medium",
  "warnings": [],
  "generated_at": "2025-05-07T00:00:00Z",
  "debug": {
    "react_steps": 0,
    "rag_avg_score": 0.72,
    "tier2_triggered": false,
    "node_latencies_ms": {}
  }
}
```

**에러 응답 형식:**
```json
{
  "error": {
    "code": "agent_timeout",
    "message": "응답이 너무 오래 걸려요. 다시 시도하시거나 더 짧은 질문을 입력해주세요.",
    "request_id": "..."
  }
}
```

| HTTP | code | 발생 조건 |
|------|------|-----------|
| 422 | `validation_error` | 필드 누락 또는 형식 오류 |
| 429 | `rate_limited` | IP당 분당 5회 초과 |
| 502 | `agent_failed` | LLM structured output/schema 실패 |
| 502 | `rag_unavailable` | ChromaDB 미설치, collection 없음, query 실패 |
| 504 | `agent_timeout` | 25초 초과 |
| 500 | `agent_internal` | 예상하지 못한 내부 예외 |

---

### `GET /api/health`

Chroma RAG collection 상태 및 서버 업타임 반환.

```json
{
  "status": "degraded",
  "patch_version": "17.2",
  "rag_chunks": {
    "units": 0, "traits": 0, "items": 0, "augments": 0,
    "deck_templates": 64, "playbook": 0, "patch_summary": 199, "glossary": 0
  },
  "uptime_s": 3601
}
```

`status`가 `degraded`이면 RAG 인덱스 중 일부가 비어 있는 상태입니다.

---

### `GET /api/patch-info`

```json
{
  "patch_version": "17.2",
  "last_updated": "2026-05-06T17:25:14+00:00",
  "warnings": []
}
```

---

### `POST /api/feedback`

```json
{
  "request_id": "X-Request-ID 헤더 값",
  "rating": 4,
  "comment": "덱 설명이 명확해요",
  "deck_clicked": "마스터 이 킨드레드"
}
```

---

### `GET /api/example-questions`

프론트엔드 입력창 힌트용 예시 4개 반환.

---

### `GET /api/_internal/cache-stats`

관리자 전용. `X-Admin-Token` 헤더 필요.

```bash
curl http://localhost:8000/api/_internal/cache-stats \
  -H "X-Admin-Token: dev-admin"
```

---

## 요청 흐름

```
POST /api/recommend
  1. RequestIdMiddleware   — uuid4 발급, X-Request-ID 헤더 설정
  2. LoggingMiddleware     — request_start 로그 (structlog console/json)
  3. Rate Limit            — IP당 5req/min (slowapi)
  4. Pydantic 검증         — tier / play_style / question
  5. cache_lookup          — tier / play_style / patch / question preview 로그
  6. cache_hit             — hit → 즉시 반환 (X-Cache: HIT)
  7. cache_miss            — miss → Semaphore(8) 획득 후 Strategy Agent 시작
  8. Strategy Agent        — intent → RAG → live route → meta → recommend → grounding 로그
  9. RAG                   — query plan, collection별 search hit/score/latency 로그
 10. Live Research         — 실행 시 step plan/observe/extract 로그
 11. cache_store           — L1 + L2 캐시 저장 (TTL 7일, patch_version 키 포함)
 12. request_done          — status_code / latency_ms / cache 로그
```

로컬에서 Uvicorn access log가 너무 시끄러우면 다음처럼 끄고 앱 flow 로그만 볼 수 있습니다.

```bash
uvicorn app.main:app --reload --port 8000 --no-access-log
```

---

## 캐시 구조

### 캐시 키 정규화

동일한 의미의 질문이 같은 키로 매핑됩니다.

```
"골드 추천해줘?"  →  normalize  →  "골드 추천해줘"
"골드  추천해줘!" →  normalize  →  "골드 추천해줘"

cache_key = sha256("GOLD|stable_top4|골드 추천해줘|17.2")
```

### 레이어

| 레이어 | 도구 | 크기 | TTL |
|--------|------|------|-----|
| L1 | `LRUCache` (in-memory) | 1000 항목 | 프로세스 생존 기간 |
| L2 | SQLite (`deckguru.db`) | 무제한 | 7일 |

패치 버전이 바뀌면 캐시 키가 달라져 자동으로 miss 처리됩니다.

---

## 테스트 실행

```bash
cd backend
python -m pytest tests/ -v
```

| 테스트 파일 | 내용 |
|-------------|------|
| `test_cache.py` | `normalize_question()`, `cache_key()` 단위 테스트 |
| `test_recommend.py` | `/api/recommend` 통합 테스트 (Mock Agent 사용) |
| `test_health.py` | `/api/health`, `/api/patch-info`, `/api/example-questions` |

테스트는 매 실행마다 임시 DB를 사용하므로 캐시 상태에 영향받지 않습니다.

---

## 팀원 연동 가이드

### Agent-1 (Strategy Agent) → Backend

`app/services/strategy_invoker.py`의 `run_strategy_agent()` 함수 내부만 교체하면 됩니다.

```python
# 현재 (Mock)
async def run_strategy_agent(request_id, tier, play_style, question, *, patch_version, timeout_s=25.0):
    data = json.loads(MOCK_PATH.read_text("utf-8"))
    ...
    return RecommendationResponse(**data)

# 교체 후 (실제 Agent)
async def run_strategy_agent(request_id, tier, play_style, question, *, patch_version, timeout_s=25.0):
    from app.agents.strategy.graph import build_graph
    graph = build_graph()
    result = await graph.ainvoke(StrategyState(
        request_id=request_id,
        tier=tier,
        play_style=play_style,
        question=question,
        patch_version=patch_version,
    ))
    return result.to_recommendation_response()
```

**반환 타입은 반드시 `RecommendationResponse`** (schemas/api.py 참조).

---

### Agent-2 (RAG) → Backend

`backend/scripts/build_rag.py`가 `data/rag/processed/`의 JSONL을 ChromaDB collection으로 빌드합니다. 현재 1차 빌드 대상은 `patch_summary`, `deck_templates`입니다.

```bash
EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  backend/.venv/bin/python -m backend.scripts.build_rag build --patch 17.2

EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  backend/.venv/bin/python -m backend.scripts.build_rag refresh --index deck_templates --patch 17.2

backend/.venv/bin/python -m backend.scripts.build_rag whitelist --patch 17.2 --out /tmp/whitelist.json
```

ChromaDB 빌드 완료 후 `CHROMA_PATH`를 `.env`에 설정하면 `/api/recommend`와 `/api/health`가 같은 collection을 참조합니다.

---

### Frontend → Backend

CORS는 `http://localhost:3000`이 허용돼 있습니다.  
추가 도메인이 필요하면 `app/main.py`의 `allow_origins` 리스트에 추가해주세요.

---

## Docker

```bash
# 빌드
docker build -t deckguru-backend .

# 실행
docker run -p 8000:8000 \
  -e PATCH_VERSION=17.2 \
  -e ADMIN_TOKEN=my-secret \
  -v $(pwd)/../data:/app/../data \
  deckguru-backend
```
