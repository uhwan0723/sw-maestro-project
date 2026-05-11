# 모닝 브리핑 에이전트 (16조)

아침 기상 직후 사용자에게 오늘의 날씨와 주요 뉴스를 1분 안에 요약하여 전달하는
LLM 기반 모닝 브리핑 에이전트 웹 서비스입니다.

## 역할 분담

| 영역 | 담당 | 디렉터리 |
|---|---|---|
| 뉴스 (외부 API + LLM 가공) | 전예준 | `backend/app/services/news.py` |
| 날씨 (외부 API + LLM 가공) | 배영빈 | `backend/app/services/weather.py` |
| BE 코어 | 김민준 | `backend/app/` 그 외 전체 |
| FE (Streamlit) | 김민솔 | `frontend/` |
| 발표 | 김현승 | `docs/`, 데모 시나리오 |

## 빠른 실행

```bash
# 1. 환경변수 준비
cp backend/.env.example backend/.env
# backend/.env 파일을 열어 UPSTAGE_API_KEY와 외부 API 키를 입력합니다.

# 2. 백엔드 로컬 실행 (개발용)
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8001
# 브라우저에서 http://localhost:8001/docs (Swagger) 접속

# 3. 프론트엔드 로컬 실행 (다른 터미널)
cd frontend
uv sync
uv run streamlit run streamlit_app.py
# 브라우저에서 http://localhost:8002 접속

# 4. 백엔드 테스트
cd backend
uv run pytest

# 5. 전체 컨테이너 실행 (백엔드 8001 + 프론트엔드 8002 동시)
docker compose up --build
```

프론트엔드 단독 가이드는 [frontend/README.md](frontend/README.md) 참고.

## API

- `GET /api/v1/health` — 서버 상태 확인
- `POST /api/v1/briefing` — 통합 브리핑 생성

요청 예시:
```json
{
  "location": "서울",
  "categories": ["IT", "경제"],
  "length": "medium"
}
```

응답 예시:
```json
{
  "weather": {
    "location": "서울",
    "temperature_min": 10.0,
    "temperature_max": 18.0,
    "precipitation_probability": 70,
    "pm25": 35,
    "pm10": 55,
    "summary": "서울 오늘 10~18°C, 오후 강수 70%, 미세먼지 보통",
    "fetched_at": "2026-05-05T07:30:00Z"
  },
  "news": [
    {
      "category": "IT",
      "items": [
        {
          "title": "...",
          "summary": "...",
          "url": "https://...",
          "published_at": "2026-05-05T06:00:00Z"
        }
      ]
    }
  ],
  "action_tip": "비가 오니 우산을 챙기시고, 출근길 IT 헤드라인 1건을 확인하시기 바랍니다",
  "integrated_summary": "오늘 서울은 10~18°C, ...",
  "generated_at": "2026-05-05T07:30:01Z",
  "degraded": []
}
```

`degraded` 필드는 부분 실패 상태를 나타냅니다.
- `["weather"]` — 날씨 수집 실패. 뉴스와 LLM 통합 응답을 제공합니다.
- `["news"]` — 뉴스 수집 실패. 날씨만으로 LLM 통합 응답을 제공합니다.
- `["weather", "news"]` — 둘 다 실패. LLM을 호출하지 않고 안내 문구만 제공합니다.
- `["llm"]` — LLM 호출 실패. 원시 데이터 기반 폴백 텍스트를 사용합니다.

### Swagger UI로 직접 검증

서버 실행 후 브라우저에서 `http://localhost:8001/docs`에 접속하면 FastAPI가 자동
생성한 Swagger UI를 통해 모든 엔드포인트를 직접 호출할 수 있습니다. `Try it out`
버튼으로 요청 본문을 입력하면 실시간으로 응답·상태 코드·헤더를 확인할 수 있어
별도의 API 클라이언트 없이도 검증이 가능합니다.

## 처리 흐름

`POST /api/v1/briefing` 호출이 응답까지 도달하는 경로는 다음과 같습니다.

```
[Client]
   │  POST /api/v1/briefing
   ▼
[uvicorn (ASGI 서버)]
   ▼
[CORSMiddleware]                                  ── app/main.py
   ▼
[router.post("/briefing")]                        ── app/api/routes.py
   │  Pydantic 자동 검증 (BriefingRequest)
   │  검증 실패 시 422 즉시 반환
   ▼
[build_briefing(req)]                             ── app/services/briefing.py
   │
   ├─ ① cache.get(key)  ──hit──► 응답 즉시 반환 (LLM 호출 0회)
   │                              ── app/core/cache.py
   │
   ├─ ② asyncio.gather(
   │       fetch_weather()  ──► 배영빈 모듈 ──► OpenWeatherMap API
   │       fetch_news()     ──► 전예준 모듈 ──► NewsAPI / 네이버
   │     )                                  (return_exceptions=True)
   │
   ├─ ③ 부분 실패 분류 → degraded 리스트 채움
   │
   ├─ ④ if (weather is None and not news):
   │       return 안내 문구 응답 (LLM 호출 0회)
   │
   ├─ ⑤ _llm_integrate(weather, news, length)
   │       │
   │       ├─ SYSTEM_PROMPT + build_user_prompt()  ── app/prompts/briefing.py
   │       │
   │       └─ LLMClient.generate_json()            ── app/core/llm.py
   │              │
   │              └─ POST api.upstage.ai/v1/chat/completions
   │                   (response_format=json_object)
   │
   │     실패 시 → fallback_text() 사용, degraded += ["llm"]
   │
   ├─ ⑥ BriefingResponse 조립
   ├─ ⑦ cache.set(key, response)
   ▼
[router 반환]
   ▼
[FastAPI 직렬화 (response_model=BriefingResponse)]
   ▼
[CORSMiddleware (응답 헤더 추가)]
   ▼
[uvicorn → Client]
   │  200 OK + JSON
   ▼
[Client]
```

### 단계별 설명

| 단계 | 설명 |
|---|---|
| ① 캐시 조회 | `(location, categories, length)` 키로 10분 TTL 캐시 조회. 적중 시 외부/LLM 호출 0회로 즉시 반환합니다. |
| ② 병렬 수집 | `asyncio.gather`로 날씨·뉴스 외부 호출을 동시에 진행합니다. 한쪽 대기 중에 다른 쪽이 진행되어 응답 시간이 직렬 호출의 절반 수준으로 단축됩니다. |
| ③ 부분 실패 분류 | 두 호출 결과 중 예외가 발생한 슬롯을 `None`/`[]`로 대체하고 `degraded` 리스트에 기록합니다. 정상 슬롯은 그대로 보존합니다. |
| ④ 단락 평가 | 두 슬롯이 모두 실패한 경우 LLM 호출을 생략하고 안내 문구만 응답하여 비용을 절감합니다. |
| ⑤ LLM 통합 요약 | Upstage Solar에 `response_format=json_object`로 요청하여 `action_tip` + `integrated_summary`를 한 번의 호출로 추출합니다. 실패 시 원시 데이터 기반 폴백 텍스트를 사용합니다. |
| ⑥ 응답 조립 | `BriefingResponse` Pydantic 모델로 직렬화 가능한 형태로 묶습니다. |
| ⑦ 캐시 저장 | 동일 키 재호출에 대비해 응답 객체를 캐시에 저장합니다. |

## 팀원 모듈 작성 가이드 (영빈 · 예준)

BE 코어는 `app/services/{weather,news}.py`의 시그니처와 `app/schemas/{weather,news}.py`의
반환 스키마를 미리 정의해 두었습니다. 아래 계약을 준수하면 BE/FE/모듈 작업이 서로
독립적으로 진행될 수 있습니다.

### 1. 함수 시그니처 준수

```python
# app/services/weather.py — 배영빈
async def fetch_weather(location: str) -> WeatherData: ...

# app/services/news.py — 전예준
async def fetch_news(categories: list[str], limit: int = 5) -> list[NewsResult]: ...
```

### 2. 반환 타입은 정의된 Pydantic 모델 사용

`app/schemas/weather.py`의 `WeatherData`, `app/schemas/news.py`의 `NewsResult`/`NewsItem`을
import하여 사용합니다.

### 3. 실패 시 도메인 예외만 사용

```python
from app.core.errors import WeatherError, NewsError

# 외부 API 실패, 응답 파싱 실패, 위치 미지원 등의 경우
raise WeatherError("OpenWeatherMap 응답 코드 404")
```

서비스 계층에서는 `HTTPException`을 사용하지 않습니다. BE 코어가 도메인 예외를
`degraded` 필드로 변환하여 클라이언트에 전달합니다.

### 4. LLM 호출은 공용 래퍼 사용

```python
from app.core.llm import get_llm

async def fetch_news(categories, limit=5):
    raw_articles = await call_news_api(...)
    llm = get_llm()
    summarized = []
    for article in raw_articles:
        summary = await llm.generate_text(
            system="아래 기사를 한 문장으로 한국어 존댓말로 요약합니다. 정치적 평가는 제외합니다.",
            user=article.body,
        )
        summarized.append(NewsItem(title=..., summary=summary, ...))
    return [...]
```

공용 래퍼를 사용하면 LLM 제공자 변경 시 `app/core/llm.py` 한 곳만 수정하면 됩니다.

### 5. 환경변수는 `app/core/config.py`에 추가

`Settings` 클래스에 필드를 추가하고 `.env.example`에 키를 명시합니다. `.env` 파일은
저장소에 커밋하지 않습니다.

## 디렉터리 구조

```
morning-briefing/
├── backend/
│   ├── app/
│   │   ├── api/routes.py            # /briefing, /health
│   │   ├── core/
│   │   │   ├── config.py            # 환경변수 (pydantic-settings)
│   │   │   ├── llm.py               # Upstage Solar 비동기 래퍼
│   │   │   ├── cache.py             # 10분 TTL 메모리 캐시
│   │   │   └── errors.py            # WeatherError / NewsError / LLMError
│   │   ├── schemas/                 # 인터페이스 계약 (전 팀이 import)
│   │   ├── services/
│   │   │   ├── weather.py           # 배영빈 영역
│   │   │   ├── news.py              # 전예준 영역
│   │   │   └── briefing.py          # 오케스트레이터 (BE)
│   │   ├── prompts/briefing.py      # 통합 요약 시스템/유저 프롬프트
│   │   └── main.py                  # FastAPI app + lifespan + CORS
│   ├── tests/                       # pytest (부분 실패 매트릭스)
│   ├── pyproject.toml               # uv
│   ├── Dockerfile
│   └── .env.example
├── frontend/                        # 김민솔 영역 (Streamlit)
│   ├── streamlit_app.py             # 진입점
│   ├── app/
│   │   ├── api_client.py            # 백엔드 호출 + 도메인 예외
│   │   ├── config.py                # BACKEND_URL, 타임아웃
│   │   ├── constants.py             # 도시/카테고리 옵션
│   │   ├── mock_data.py             # 5가지 시나리오 mock (개발 모드)
│   │   ├── schemas.py               # 백엔드 contract 미러링
│   │   └── components/
│   │       └── briefing_view.py     # 카드 UI 렌더
│   ├── .streamlit/config.toml
│   ├── Dockerfile
│   └── pyproject.toml
├── docker-compose.yml
└── README.md
```

## 테스트

`backend/tests/test_briefing.py`는 오케스트레이터의 부분 실패 매트릭스를 검증합니다.

| 시나리오 | 검증 내용 |
|---|---|
| 정상 경로 | weather + news + LLM 모두 성공, `degraded=[]` |
| weather 실패 | `degraded=["weather"]`, 뉴스만으로 LLM 호출 |
| news 실패 | `degraded=["news"]`, 날씨만으로 LLM 호출 |
| 둘 다 실패 | LLM 미호출, 안내 문구 응답 |
| LLM 실패 | `degraded=["llm"]`, 폴백 텍스트 사용 |
| 캐시 적중 | 동일 요청 재호출 시 외부/LLM 호출 0회 |

실행 방법: `cd backend && uv run pytest`

## 주의 사항

- LLM 응답을 카드 텍스트로 직접 노출하지 않습니다. structured JSON으로 받아 스키마 필드에 매핑합니다.
- 외부 API 키는 `.env` 파일에만 보관하며, 저장소에 커밋하지 않습니다.
- 정치적 평가, 사실관계 미검증 추론, 뉴스 본문 전체 재작성은 금지합니다 (기획서 §2 자율성 범위).
