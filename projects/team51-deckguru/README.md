# DeckGuru

DeckGuru는 롤토체스(TFT) 유저의 `티어`, `플레이 스타일`, 자연어 질문을 받아 현재 패치 기준 덱 추천, 운영법, 출처, 확신도를 반환하는 RAG 기반 Agentic AI 서비스입니다.

이 저장소는 기획·사양 문서, FastAPI 백엔드, Next.js 프론트엔드, RAG 데이터와 인덱싱 도구를 함께 관리합니다.

## 현재 구현 범위

- `frontend/`: Next.js App Router 기반 추천 입력 화면과 결과 화면
- `backend/`: FastAPI API 서버, Strategy Agent 호출, 캐시, rate limit, request flow 로그
- `backend/app/agents/strategy/`: LangGraph 기반 의도 분류, RAG 검색, Live Research 분기, 추천 생성, grounding 검증
- `data/rag/`: RAG raw/processed 데이터와 manifest
- `backend/scripts/build_rag.py`: processed JSONL을 ChromaDB collection으로 빌드
- `services/rag/`: RAG 수집·가공 실험용 도구와 이전 인덱싱 스크립트
- `docs/specs/`: 프로젝트 사양, API 계약, 역할 분담 문서

현재 RAG 데이터는 `patch_summary`와 `deck_templates`가 중심입니다. `units`, `traits`, `items`, `augments`, `playbook`, `glossary` collection은 구조상 준비되어 있지만 데이터가 비어 있을 수 있습니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | Next.js `16.1.7`, React `19.2.4`, TypeScript `5.9.3`, Tailwind CSS `4.2.1`, TanStack Query `5.100.9`, Zod `4.4.3`, pnpm `10.28.2` |
| Backend | Python `>=3.11,<3.13`, FastAPI, Pydantic v2, LangGraph, LangChain Upstage, structlog, slowapi, aiosqlite |
| RAG | ChromaDB, BGE-M3 embedding, patch-versioned JSONL |
| LLM | Upstage Solar 계열 모델 (`solar-pro2`, `solar-mini`) |

## 디렉토리 구조

```text
deckguru/
├── frontend/                 # Next.js 프론트엔드
├── backend/                  # FastAPI 백엔드와 Strategy/RAG runtime
│   ├── app/
│   │   ├── api/              # /api/recommend, /api/patch-info 등
│   │   ├── agents/strategy/  # LangGraph Strategy Agent
│   │   ├── rag/              # Chroma 기반 RagService
│   │   ├── research/         # Live Research 보조 루프
│   │   └── services/         # cache, limiter, strategy invoker
│   ├── scripts/              # RAG build, live research 수동 점검
│   └── tests/
├── data/rag/                 # raw/processed RAG 데이터와 vectorstore 위치
├── services/rag/             # RAG 수집·가공 실험 도구
├── models/                   # 로컬 embedding 모델 저장 위치
└── docs/specs/               # 프로젝트 사양 문서
    ├── 00-overview.md
    ├── 01-architecture.md
    ├── 02-agent-strategy-spec.md
    ├── 03-agent-rag-spec.md
    ├── 04-agent-research-spec.md
    ├── 05-backend-spec.md
    ├── 06-frontend-spec.md
    ├── 07-data-contracts.md
    └── 08-roles-and-handoffs.md
```

## 빠른 실행

화면 흐름만 확인하려면 프론트엔드 mock 모드가 가장 빠릅니다.

```bash
cd frontend
pnpm install
cp .env.local.example .env.local
```

`frontend/.env.local`에서 mock을 켭니다.

```bash
NEXT_PUBLIC_USE_MOCK=true
```

프론트엔드를 실행합니다.

```bash
pnpm dev
```

브라우저에서 `http://localhost:3000`에 접속합니다.

## 백엔드와 연결해서 실행

백엔드와 실제 API 흐름을 확인하려면 FastAPI 서버를 먼저 실행합니다.

```bash
cd backend
python -m venv .venv
.venv/bin/python -m pip install -e ".[backend,dev,rag]"
cp .env.example .env
```

`backend/.env`에서 최소한 아래 값을 확인합니다.

```bash
PATCH_VERSION=17.2
CHROMA_PATH=../data/rag/vectorstore/chroma
EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3
UPSTAGE_API_KEY=
MOCK_STRATEGY_AGENT=false
APP_LOG_FORMAT=console
```

처음 실행하는 환경에서는 BGE-M3 모델과 Chroma vectorstore가 필요합니다.

```bash
cd /Users/dongwoo/Projects/deckguru
mkdir -p models
backend/.venv/bin/hf download BAAI/bge-m3 --local-dir models/bge-m3

EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  backend/.venv/bin/python -m backend.scripts.build_rag build --patch 17.2
```

백엔드를 실행합니다. Uvicorn access log를 줄이면 앱 내부 flow 로그를 더 읽기 쉽습니다.

```bash
cd backend
EMBEDDING_MODEL=/Users/dongwoo/Projects/deckguru/models/bge-m3 \
  uvicorn app.main:app --reload --port 8000 --no-access-log
```

상태를 확인합니다.

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/patch-info
```

프론트엔드는 같은 origin의 `/api/*`를 백엔드로 rewrite합니다.

```bash
cd frontend
cp .env.local.example .env.local
```

`frontend/.env.local`을 다음처럼 설정합니다.

```bash
NEXT_PUBLIC_USE_MOCK=false
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=
```

프론트엔드를 실행합니다.

```bash
pnpm dev
```

## 주요 API

### `POST /api/recommend`

티어, 플레이 스타일, 질문을 받아 추천 결과를 반환합니다.

```bash
curl http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "GOLD",
    "play_style": "stable_top4",
    "question": "현재 패치에서 골드가 티어 올리기 좋은 덱 추천해줘"
  }'
```

응답 헤더에는 `X-Request-ID`, `X-Cache`, `X-Patch-Version`이 포함됩니다.

### `GET /api/patch-info`

현재 백엔드가 기준으로 삼는 패치 버전과 RAG 데이터 갱신 정보를 반환합니다.

```bash
curl http://localhost:8000/api/patch-info
```

### `GET /api/health`

서버 상태와 Chroma collection별 chunk 수를 반환합니다.

```bash
curl http://localhost:8000/api/health
```

## 요청 흐름

```text
Frontend
  → POST /api/recommend
Backend
  → cache lookup
  → Strategy Agent
  → intent classification
  → RAG query plan
  → Chroma collection search
  → optional Live Research
  → meta analysis
  → recommendation generation
  → grounding verification
  → response formatting
  → cache store
```

로컬 기본 로그는 `APP_LOG_FORMAT=console`입니다. 같은 `request_id`로 `cache`, `strategy`, `intent`, `rag`, `research`, `meta`, `recommend`, `grounding`, `response` 단계를 따라갈 수 있습니다.

JSON 로그가 필요하면 `backend/.env`에서 다음처럼 변경합니다.

```bash
APP_LOG_FORMAT=json
```

## RAG 데이터와 vectorstore

`data/rag/processed/`의 JSONL과 manifest는 Chroma collection의 입력입니다.

```text
data/rag/
├── raw/          # 원천 수집 데이터
├── processed/    # schema 검증이 끝난 JSONL과 current_patch.json
├── seeds/        # 직접 작성하는 glossary/playbook seed
└── vectorstore/  # 로컬 Chroma 산출물 위치
```

`data/rag/vectorstore/chroma/`는 로컬 빌드 산출물이므로 git에 커밋하지 않습니다. 새 패치 데이터가 들어오면 raw/processed 데이터를 갱신한 뒤 `backend.scripts.build_rag`로 Chroma를 다시 빌드합니다.

## 프론트엔드 동작 주의사항

추천 결과 화면은 React Query cache handoff 기반입니다.

1. 메인 화면에서 추천 요청을 보냅니다.
2. 성공 응답을 `request_id` 기준으로 캐시에 저장합니다.
3. `/recommendations/{requestId}`로 이동합니다.
4. 결과 화면은 캐시에 저장된 응답을 렌더링합니다.

따라서 결과 URL을 새로고침하거나 직접 열면 캐시가 비어 있어 빈 상태 화면이 표시될 수 있습니다.

## 검증 명령

백엔드:

```bash
backend/.venv/bin/python -m ruff check backend
backend/.venv/bin/python -m pytest backend/tests -q
```

프론트엔드:

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm build
```

실제 백엔드 연결 smoke test:

```bash
curl http://localhost:8000/api/patch-info
curl http://localhost:8000/api/health
curl http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"tier":"GOLD","play_style":"stable_top4","question":"현재 패치 추천 덱 알려줘"}'
```

## 문서 읽는 순서

프로젝트 전체 맥락을 잡을 때는 아래 순서로 읽습니다.

| 순서 | 문서 | 목적 |
| --- | --- | --- |
| 1 | [`docs/specs/00-overview.md`](./docs/specs/00-overview.md) | 제품 목표, 설계 원칙, MVP 범위 확인 |
| 2 | [`docs/specs/01-architecture.md`](./docs/specs/01-architecture.md) | 전체 시스템 구조 확인 |
| 3 | [`docs/specs/07-data-contracts.md`](./docs/specs/07-data-contracts.md) | API와 데이터 schema 확인 |
| 4 | [`docs/specs/08-roles-and-handoffs.md`](./docs/specs/08-roles-and-handoffs.md) | 역할 분담과 handoff 확인 |
| 5 | `backend/README.md` | 백엔드 실행, API, 로그, RAG 빌드 확인 |
| 6 | `frontend/README.md` | 프론트엔드 실행, mock, API 연결 확인 |
| 7 | `data/rag/README.md` | RAG 데이터 정책과 현재 인덱스 확인 |

담당 영역별 세부 사양은 `docs/specs/02-agent-strategy-spec.md`, `docs/specs/03-agent-rag-spec.md`, `docs/specs/04-agent-research-spec.md`, `docs/specs/05-backend-spec.md`, `docs/specs/06-frontend-spec.md`를 참고합니다.

## 개발 원칙

1. Grounding-First: 응답의 기물, 아이템, 특성, 증강체 이름은 RAG 근거와 whitelist를 기준으로 검증합니다.
2. Patch-Versioned: 모든 검색과 응답은 `patch_version`을 기준으로 필터링합니다.
3. Schema-First: API와 데이터 계약은 `docs/specs/07-data-contracts.md`와 backend/frontend schema에 먼저 반영합니다.
4. Source-Mandatory: 외부 사실은 `sources[]`와 연결합니다.
5. Deterministic Post-processing: 추천 후처리는 가능한 한 결정적 규칙으로 처리합니다.

## 현재 한계

- 실제 추천 경로는 `UPSTAGE_API_KEY`, BGE-M3 모델, Chroma vectorstore가 준비되어야 정상 동작합니다.
- RAG collection 일부는 아직 데이터가 비어 있을 수 있습니다.
- Live Research는 외부 검색과 페이지 fetch 결과에 따라 실행 시간과 결과가 달라질 수 있습니다.
- 프론트엔드 결과 페이지는 현재 cache handoff 기반이라 직접 URL 접근을 영속 조회로 복원하지 않습니다.
- `services/rag/`에는 Windows 경로 예시가 일부 남아 있습니다. 현재 백엔드 runtime 기준 RAG 빌드는 `backend/scripts/build_rag.py`를 우선 사용합니다.
