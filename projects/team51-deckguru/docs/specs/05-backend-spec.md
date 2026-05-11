# 05. Backend — FastAPI Gateway

> 담당: Backend
> 범위: HTTP 라우팅, Pydantic 검증, Strategy Agent 호출 오케스트레이션, 캐싱, 로깅, rate limit, 에러 처리, 배포
> 의존:
> - `02-agent-strategy-spec.md`의 `run_strategy_agent()` 함수
> - `03-agent-rag-spec.md`의 `RagService.count_chunks()` / `current_patch_version()`
> - `06-frontend-spec.md`의 호출 측
> - `07-data-contracts.md` (단일 진실 소스)

---

## 1. 책임 범위

| 포함 | 제외 |
|---|---|
| FastAPI 라우터, Pydantic v2 검증, 미들웨어 | LangGraph 노드 (Agent1) |
| 응답 캐싱 (L1 LRU + L2 SQLite, patch-keyed) | RAG 인덱싱 (Agent2) |
| Rate limit, timeout, semaphore | 외부 웹 크롤링 (Agent3) |
| CORS, request_id, JSON 로깅 | UI 렌더링 (Frontend) |
| 에러 → HTTP 매핑, 사용자 친화 메시지 | LLM 프롬프트 |
| Mock fixture (Frontend 병렬 개발용) | |
| Dockerfile + 로컬 개발 환경 | |

---

## 2. 기술 스택

| 도구 | 용도 |
|---|---|
| FastAPI | ASGI 라우터 |
| Uvicorn | ASGI 서버 |
| Pydantic v2 | 요청/응답 검증, schema 단일 진실 소스 |
| structlog | JSON 구조화 로깅 |
| slowapi | rate limit |
| cachetools | L1 LRU |
| SQLite (`aiosqlite`) | L2 캐시 + feedback store |
| httpx | (Agent/Research가 사용하는 외부 클라이언트의 통합 timeout) |
| pydantic-settings | env 로드 + fail-fast |

---

## 3. API 엔드포인트

`07-data-contracts.md` §5와 함께 봐야 한다 (요청/응답 schema는 거기).

### 3.1 `POST /api/recommend` — 메인 추천

| 항목 | 내용 |
|---|---|
| Request | `RecommendRequest` (07-data-contracts §5.1) |
| Response 200 | `RecommendationResponse` (07-data-contracts §4) |
| Errors | 400/422/429/502/504 (§3.7) |

처리 흐름:
```
1. Pydantic 검증 (자동, FastAPI)
2. request_id 발급 (uuid4)
3. cache lookup (key = sha256(tier|style|norm(q)|patch))
4. cache hit → return
5. cache miss:
   - Semaphore acquire (max 8)
   - asyncio.wait_for(run_strategy_agent(...), timeout=25)
   - response normalize (URL https:// 강제, sources 길이 cap)
   - cache put (TTL 1h)
6. 로그 기록 + 응답 반환
```

### 3.2 `GET /api/health`

```json
{
  "status": "ok",
  "patch_version": "14.9",
  "rag_chunks": {
    "units": 60, "items": 28, "deck_templates": 18, "...": "..."
  },
  "uptime_s": 3601
}
```

`rag_chunks`의 어떤 collection이 0이면 `status = "degraded"`.

### 3.3 `GET /api/patch-info`

UI 헤더에 표시할 기준 패치 정보.

```json
{
  "patch_version": "14.9",
  "last_updated": "2025-05-04T03:00:00Z",
  "warnings": []
}
```

`patch_age_days <= 1`이면 `warnings: ["data_may_be_insufficient_after_patch"]`.

### 3.4 `POST /api/feedback` — 만족도

```json
{
  "request_id": "...",
  "rating": 4,
  "comment": "...",
  "deck_clicked": "9코스트 정밀"
}
```

SQLite `feedback` 테이블에 단순 저장. 분석 대시보드는 MVP 미포함.

### 3.5 `GET /api/example-questions`

Frontend 예시 칩 lazy load용.

```json
[
  {"intent": "recommend_deck", "text": "현재 패치에서 골드가 티어 올리기 좋은 덱 3개 추천해줘"},
  {"intent": "deck_playstyle", "text": "요즘 많이 나오는 덱 하나 골라서 초반부터 후반까지 운영법 알려줘"},
  {"intent": "item_pivot",     "text": "초반에 곡궁이 많이 나왔는데 어떤 덱 가면 좋아?"},
  {"intent": "patch_summary",  "text": "이번 롤토체스 패치에서 메타에 영향 큰 변경점만 알려줘"}
]
```

### 3.6 `GET /api/_internal/cache-stats` (관리자)

```json
{"l1_size": 47, "l2_size": 230, "hit_rate_24h": 0.34}
```

`X-Admin-Token` 헤더로 보호. 데모 PC에서만 노출.

### 3.7 에러 응답

```json
{
  "error": {
    "code": "agent_timeout",
    "message": "응답이 너무 오래 걸려요. 다시 시도하시거나 더 짧은 질문을 입력해주세요.",
    "request_id": "..."
  }
}
```

| HTTP | code | 의미 |
|---|---|---|
| 400 | `validation_error` | Pydantic 검증 실패 |
| 422 | `intent_unsupported` | Agent intent=other → 기본 안내 |
| 429 | `rate_limited` | IP당 분당 호출 초과 |
| 500 | `agent_internal` | Agent 내부 예외 |
| 502 | `rag_unavailable` | ChromaDB 접근 실패 |
| 502 | `agent_failed` | LLM schema fail 2회 연속 |
| 504 | `agent_timeout` | 25s 초과 |

---

## 4. 미들웨어 / 처리 파이프라인

```
[Request]
  → CORS
  → request_id 발급 (uuid4) + X-Request-ID 응답 헤더
  → 로깅 시작 (event=request_start)
  → rate limit (slowapi)
  → router (Pydantic 자동 검증)
  → cache layer
  → semaphore (max 8)
  → run_strategy_agent (asyncio.wait_for, 25s)
  → 응답 정규화
  → cache put
  → 로깅 종료 (event=request_done, latency, intent, confidence)
[Response]
```

### 4.1 캐싱 (반드시 구현)

기획서가 누락한 부분. P50≤15s SLA 달성에 필수.

| 레이어 | 도구 | 크기 | TTL |
|---|---|---|---|
| L1 | `cachetools.LRUCache` (in-process) | 1000 entries | (LRU만, TTL 없음) |
| L2 | SQLite | 무제한 | 7d |

**Cache key:**
```python
def cache_key(req: RecommendRequest, patch: str) -> str:
    norm_q = normalize_question(req.question)  # 소문자 + 공백 정규화 + 조사/구두점 제거
    raw = f"{req.tier}|{req.play_style}|{norm_q}|{patch}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

`normalize_question`:
- NFC unicode 정규화
- 소문자
- 연속 공백 1개로
- `?!~.…` 같은 trailing 구두점 제거
- 한국어 조사 trailing 제거 (선택, 정확도 trade-off)

**캐시 무효화:** patch_version이 바뀌면 자동 miss (key에 포함). 명시적 flush API는 미포함.

### 4.2 Rate limit

slowapi:
- IP당 `5 req / min`, `60 req / hour`
- `DEMO_MODE=true`면 한도 100/1000으로 완화

### 4.3 Timeout

- Agent 호출: `asyncio.wait_for(..., timeout=25.0)` → TimeoutError → 504
- HTTP 응답 timeout: 30s (Frontend SLA와 일치)
- Live Research 내부 timeout 15s는 Agent3 책임

### 4.4 동시성 제한

```python
agent_semaphore = asyncio.Semaphore(8)

async with agent_semaphore:
    response = await asyncio.wait_for(run_strategy_agent(...), timeout=25)
```

LLM rate limit + 비용 폭주 방지.

---

## 5. CORS

```python
allow_origins = [
    "http://localhost:3000",
    "https://deckguru.example.com",   # 데모 배포 URL (5/7 결정)
]
allow_methods = ["GET", "POST"]
allow_headers = ["Content-Type", "X-Admin-Token"]
allow_credentials = False             # MVP는 쿠키 미사용
```

---

## 6. 로깅 (structlog JSON)

모든 요청은 `request_id` (uuid4) 발급 + `X-Request-ID` 응답 헤더 + 로그 라인.

**필드:**
```json
{"ts":"...","level":"info","event":"request_done","request_id":"...","tier":"GOLD",
 "play_style":"stable_top4","intent":"recommend_deck","confidence":"high",
 "latency_ms":12340,"cache":"miss","decks":3,"sources":4,"warnings":[],
 "react_steps":0,"tokens_in":2400,"tokens_out":820}
```

PII는 없음. `question` 본문은 별도 파일(`logs/questions.jsonl`)로 분리 저장 (평가 골든셋 후보).

LLM raw response는 7일 보관 — 디버깅 + 회귀 테스트.

---

## 7. 설정 (`.env`)

```
APP_ENV=local                    # local | staging | production
LLM_PROVIDER=openai              # openai | anthropic | local
LLM_API_KEY=...
LLM_MODEL=gpt-4o-mini            # 4/29 합의
LLM_MODEL_SMALL=gpt-4o-mini      # intent 분류용
EMBEDDING_MODEL=BAAI/bge-m3
CHROMA_PATH=./data/chroma
PATCH_VERSION=14.9
DEMO_MODE=false
LOG_LEVEL=INFO
ADMIN_TOKEN=...
TAVILY_API_KEY=...               # Live Research용
```

`pydantic-settings`로 로드. 누락 시 startup fail-fast.

---

## 8. Mock Agent (Frontend 병렬 개발용)

`tests/conftest.py`에서 `run_strategy_agent`를 monkeypatch하여 고정 응답 반환. **Day 2(4/30)에 합의**된 mock fixture는 `tests/fixtures/mock_responses/` 아래에 둔다.

```python
# tests/fixtures/mock_responses/recommend_deck_gold_stable.json
{
  "request_id": "mock-...",
  "patch_version": "14.9",
  "intent": "recommend_deck",
  "meta_summary": "...",
  "decks": [...],
  ...
}
```

Frontend는 `NEXT_PUBLIC_API_BASE=http://localhost:8000`이거나 별도 `mock-server` 모드(`NEXT_PUBLIC_USE_MOCK=true`)에서 이 JSON을 직접 import.

---

## 9. 디렉토리 구조

```
backend/
├── app/
│   ├── main.py                 # FastAPI 인스턴스
│   ├── api/
│   │   ├── __init__.py
│   │   ├── recommend.py
│   │   ├── health.py
│   │   ├── patch_info.py
│   │   ├── feedback.py
│   │   └── examples.py
│   ├── middleware/
│   │   ├── request_id.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── services/
│   │   ├── strategy_invoker.py # run_strategy_agent 래퍼 + cache + timeout
│   │   ├── cache.py            # L1 + L2
│   │   ├── feedback_store.py
│   │   └── normalize.py        # cache key 정규화
│   ├── schemas/                # Pydantic — 07-data-contracts와 1:1
│   │   ├── api.py
│   │   ├── shared.py
│   │   └── errors.py
│   └── settings.py
├── tests/
│   ├── conftest.py             # mock fixture
│   ├── fixtures/
│   │   └── mock_responses/
│   ├── test_recommend.py
│   ├── test_cache.py
│   ├── test_health.py
│   └── test_e2e.py
├── Dockerfile
└── pyproject.toml
```

---

## 10. 테스트

| 종류 | 도구 | 대상 |
|---|---|---|
| Unit | pytest | cache key, normalize, error mapping |
| Integration | pytest + httpx AsyncClient | `/api/*` (Agent는 mock) |
| Contract | pytest | RecommendationResponse round-trip |
| E2E | pytest (실제 Agent + RAG) | 골든셋 3개 시나리오, 캐시 첫/재호출 비교 |

---

## 11. 로컬 실행

```bash
# 1. 의존
cd backend && uv sync

# 2. RAG 빌드 (Agent2가 제공)
python -m scripts.build_rag build --patch 14.9

# 3. 서버
uvicorn app.main:app --reload --port 8000

# 4. 헬스
curl http://localhost:8000/api/health
```

---

## 12. 배포 (MVP)

- Docker 단일 컨테이너 (Agent + RAG + Backend 통합).
- ChromaDB는 컨테이너 내 볼륨 마운트.
- 호스팅: fly.io / Railway 무료 티어 (1차) / 데모 PC (폴백).
- HTTPS: ngrok / Cloudflare Tunnel (데모 한정).
- 5/7까지 클라우드 선택 보류, 폴백 시나리오 보유.

---

## 13. 기획서 피드백

| # | 기획서 | 문제 | 본 spec |
|---|---|---|---|
| 1 | "/recommend, /health 등"(§5.3.2) 한 줄 | 요청/응답 schema 미정 | §3 + 07-data-contracts §5에 4개 엔드포인트 + JSON 명시 |
| 2 | 캐싱 전무 | "30s 응답" 목표인데 매번 LLM이면 SLA 위험 | §4.1 L1+L2 patch-keyed 캐시 |
| 3 | rate limit / abuse 보호 부재 | 데모 공개 URL이면 LLM 비용 폭발 위험 | §4.2 slowapi + DEMO_MODE 토글 |
| 4 | timeout 정책 | "30초"만 있음. Agent vs HTTP vs Live Research 구분 X | §4.3에 25/30/15로 분리 |
| 5 | request_id / 구조 로깅 | 디버깅·평가 필수 | §6 structlog JSON |
| 6 | 에러 처리(§4.3) 표 | 사용자 메시지만 있고 HTTP 매핑 없음 | §3.7 코드 ↔ HTTP |
| 7 | Mock fixture 부재 | Frontend가 Backend 완성을 기다리면 일정 위험 | §8 Day 2 mock 합의 |
| 8 | 환경변수 / fail-fast | LLM 키 운영 미정 | §7 .env + startup validation |
| 9 | CORS | 분리 배포면 필수 | §5 |
| 10 | 동시성 / 비용 보호 | LLM rate limit hit 시 줄줄이 실패 | §4.4 Semaphore(8) |
| 11 | UI에 기준 패치 노출 | API에 patch_info 없음 | §3.3 `/api/patch-info` |
| 12 | 피드백 분석 | 단순 평점 저장만 | §3.4 + JSONL 별도 보관, MVP는 저장만 |
