# Stockfish

AI·SW 마에스트로 17기 AI-21팀 프로젝트입니다.

Stockfish는 초보 투자자가 KOSPI 반도체·제약 섹터 흐름과 기본 투자 용어를 쉽게 이해할 수 있도록 돕는 AI 투자 교육 챗봇입니다.  
사용자는 채팅 UI에서 섹터 분석을 빠르게 요청하거나 “PER이 뭐야?” 같은 용어 질문을 할 수 있고, 백엔드는 주가 지표·뉴스 데이터·LLM 워크플로우를 조합해 교육 목적의 답변을 생성합니다.

> 본 서비스는 매수, 매도, 보유 판단이나 수익률 예측을 제공하지 않습니다. 응답은 시장 지표와 뉴스 기반의 교육용 해석입니다.

## 주요 기능

- KOSPI 반도체·제약 섹터 분석
- yfinance 기반 대표 종목 주가·등락률·거래량 수집
- 네이버 뉴스 검색 API 기반 섹터별 뉴스 수집·전처리
- LangGraph 기반 요청 분류, 컨텍스트 로딩, 가설 생성·검증, 최종 안전성 검토
- Upstage Chat Completions API 기반 구조화 LLM 응답 생성
- 투자 조언 요청 차단 및 안전 안내 분리 제공
- React Router 기반 채팅 UI, 빠른 섹터 분석 버튼, 추천 질문, 분석 카드 렌더링
- `sessionStorage` 기반 세션 ID 유지와 대화 히스토리 전달

## 프로젝트 구조

```text
projects/team21-stockfish/
├── README.md          # 공통 프로젝트 README
├── be-ai/             # FastAPI + LangGraph 기반 BE/AI 서버
│   ├── app/
│   │   ├── ai/        # LangGraph 노드, 프롬프트, LLM 응답 모델
│   │   ├── api/       # FastAPI 라우터
│   │   ├── core/      # 설정, LLM 클라이언트, 에러 처리
│   │   ├── db/        # SQLAlchemy async DB 세션과 초기화
│   │   ├── ingestion/ # yfinance, 네이버 뉴스 수집·정규화
│   │   ├── models/    # DB 모델과 도메인 enum
│   │   ├── repositories/
│   │   ├── schemas/   # API 요청·응답 스키마
│   │   └── services/  # 분석, 채팅, 컨텍스트, 수집 서비스
│   ├── tests/
│   ├── README.md
│   └── pyproject.toml
└── fe/                # React Router 기반 프론트엔드
    ├── app/
    │   ├── components/
    │   ├── hooks/
    │   ├── routes/
    │   ├── types/
    │   └── utils/
    ├── README.md
    └── package.json
```

## 기술 스택

| 영역 | 사용 기술 |
| --- | --- |
| Frontend | React 19, React Router 7, TypeScript, Vite, Tailwind CSS 4, TanStack Query, Axios, lucide-react |
| Backend / AI | Python 3.14, FastAPI, LangGraph, SQLAlchemy 2, aiosqlite, APScheduler |
| Data | yfinance, Naver News Search API, SQLite |
| LLM | Upstage Chat Completions API (`solar-pro3` 기본값) |
| Package manager | npm, uv |

## 실행 준비

### 필수 도구

- Node.js 20 이상
- Python 3.14 이상
- uv
- 네이버 검색 API 키
- Upstage API 키

### 백엔드 환경 변수

`be-ai/.env.example`을 복사해 `be-ai/.env`를 만들고 값을 채웁니다.

```bash
cd projects/team21-stockfish/be-ai
cp .env.example .env
```

| 변수명 | 설명 |
| --- | --- |
| `APP_ENV` | 실행 환경 이름 |
| `DATABASE_URL` | SQLite async DB URL. 기본 예시는 `sqlite+aiosqlite:///./data/app.db` |
| `CORS_ALLOWED_ORIGINS` | FE 접근 허용 origin 목록. JSON 문자열 형식 |
| `NAVER_CLIENT_ID` | 네이버 검색 API Client ID |
| `NAVER_CLIENT_SECRET` | 네이버 검색 API Client Secret |
| `NAVER_NEWS_DISPLAY` | 섹터별 뉴스 수집 개수. 최대 100 |
| `ENABLE_DAILY_COLLECTION_SCHEDULER` | 서버 기동 시 일 단위 자동 수집 스케줄러 활성화 여부 |
| `DAILY_COLLECTION_HOUR` | 자동 수집 실행 시각. Asia/Seoul 기준 0~23 |
| `UPSTAGE_API_KEY` | Upstage API 키 |
| `UPSTAGE_BASE_URL` | Upstage API base URL |
| `UPSTAGE_MODEL` | 사용할 Upstage 모델 |

### 프론트엔드 환경 변수

`fe/.env.example`을 복사해 `fe/.env`를 만들고 백엔드 주소를 설정합니다.

```bash
cd projects/team21-stockfish/fe
cp .env.example .env
```

| 변수명 | 설명 | 기본값 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 백엔드 API 서버 주소 | `http://127.0.0.1:8000` |

## 로컬 실행

### 1. BE-AI 서버 실행

```bash
cd projects/team21-stockfish/be-ai
uv sync

mkdir -p data
uv run python -c 'import asyncio; from app.db.init import init_db; asyncio.run(init_db())'

uv run python -m app.ingestion.manual_collect
uv run fastapi dev app/main.py
```

기본 API 서버 주소는 `http://127.0.0.1:8000`입니다. API 문서는 서버 실행 후 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

데이터 수집만 특정 기준일로 실행하려면 다음 형식을 사용할 수 있습니다.

```bash
uv run python -m app.ingestion.manual_collect --date 2026-05-10
```

### 2. FE 개발 서버 실행

별도 터미널에서 실행합니다.

```bash
cd projects/team21-stockfish/fe
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

## 주요 API

모든 API는 `/api/v1` prefix를 사용합니다.

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/sectors/{sector}/analysis?refresh=false` | 섹터 분석 조회 또는 생성 |
| `POST` | `/chat` | 사용자 채팅 요청 처리 |

지원 섹터 코드는 다음 두 가지입니다.

| 코드 | 표시명 |
| --- | --- |
| `semiconductor` | 반도체 |
| `pharmaceutical` | 제약 |

### 요청 예시

```bash
curl -X GET 'http://127.0.0.1:8000/api/v1/health'
```

```bash
curl -X GET 'http://127.0.0.1:8000/api/v1/sectors/semiconductor/analysis?refresh=true'
```

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/chat' \
  --header 'Content-Type: application/json' \
  --data '{
    "message": "PER이 뭐야?",
    "session_id": null,
    "history": []
  }'
```

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/chat' \
  --header 'Content-Type: application/json' \
  --data '{
    "message": "HBM이 반도체 섹터에 왜 중요해?",
    "sector": "semiconductor"
  }'
```

## 동작 흐름

### Frontend

1. `app/routes/home.tsx`가 채팅 화면을 렌더링합니다.
2. `useChat` 훅이 메시지 목록, 세션 ID, 히스토리, API 호출 상태를 관리합니다.
3. 섹터 빠른 버튼은 `semiconductor`, `pharmaceutical` 코드로 매핑되어 섹터 분석 API를 호출합니다.
4. 일반 질문은 `/api/v1/chat`으로 전달됩니다.
5. 응답의 `request_type`에 따라 일반 말풍선, 섹터 분석 카드, 용어 설명 카드로 렌더링합니다.

### Backend / AI

1. FastAPI가 `/api/v1/chat` 또는 `/api/v1/sectors/{sector}/analysis` 요청을 받습니다.
2. `ChatService` 또는 `AnalysisService`가 LangGraph Agent 상태를 생성합니다.
3. Agent는 안전성 검사, 요청 분류, 컨텍스트 로딩, 가설 생성, 가설 검증, 리포트 작성, 안전성 검토 노드를 실행합니다.
4. 컨텍스트 로딩 단계는 SQLite에 저장된 주가 지표와 뉴스 데이터를 읽고, 부족하면 경고를 생성합니다.
5. LLM 호출은 Upstage API에 JSON 응답 형식을 요청하고, Pydantic 모델로 검증합니다.
6. 검증된 결과만 API 응답으로 반환하며, 투자 조언성 요청은 `out_of_scope`로 차단합니다.

## 검증 명령

```bash
# FE 타입 검사 및 빌드
cd projects/team21-stockfish/fe
npm run typecheck
npm run build
```

```bash
# BE 테스트
cd projects/team21-stockfish/be-ai
uv run pytest
```

## 제출 전 확인

다음 파일과 디렉터리는 로컬 실행 산출물이거나 민감 정보이므로 제출하지 않습니다.

- `fe/node_modules/`
- `fe/.react-router/`
- `fe/build/`
- `fe/.env`
- `be-ai/.venv/`
- `be-ai/__pycache__/`, `be-ai/app/**/__pycache__/`, `be-ai/tests/**/__pycache__/`
- `be-ai/data/`
- `be-ai/.env`
- `.DS_Store`

의존성 재현을 위해 `fe/package-lock.json`과 `be-ai/uv.lock`은 함께 제출합니다.
