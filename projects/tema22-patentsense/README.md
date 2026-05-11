# PatentSense — 특허 아이디어 검증 AI 에이전트

자연어로 입력한 아이디어와 유사한 한국 특허를 KIPRIS에서 찾아 유사도를 분석하고 리포트를 생성하는 LangGraph 기반 에이전트입니다.

## 동작 흐름

```
사용자 아이디어 (자연어)
   ↓ Solar LLM
키워드 추출 (최대 5개)
   ↓ KIPRIS Plus getWordSearch
관련 특허 수집 (키워드별 30건, 중복 제거)
   ↓ Solar Embedding (코사인 유사도)
Top 5 유사 특허 랭킹
   ↓ Solar LLM
마크다운 리포트 생성
```

## 요구 사항

- Python 3.10+
- KIPRIS Plus API 키 (https://plus.kipris.or.kr)
- Solar (Upstage) API 키 (https://console.upstage.ai)

## 설치

### 1. 저장소 클론
```bash
git clone https://github.com/ASM-17-AI-22/patentsense-.git
cd patentsense-
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. API 키 설정
`.env.example`을 복사해 `.env` 파일을 만들고 본인 키를 입력합니다.

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 내용:
```
KIPRIS_API_KEY=your_kipris_api_key_here
SOLAR_API_KEY=your_solar_api_key_here
```

#### KIPRIS Plus 키 발급
1. https://plus.kipris.or.kr 회원가입
2. **데이터 서비스 > 서비스 신청 > Open API**에서 **"특허·실용 공개·등록공보"** 신청 (무료, 월 1,000건)
3. **마이페이지 > API KEY 관리**에서 발급된 키 복사

#### Solar API 키 발급
1. https://console.upstage.ai 회원가입
2. API 키 발급 페이지에서 키 생성

## 실행

### Next.js 프론트엔드
```bash
cd frontend
npm run dev
```

### Streamlit UI
```bash
streamlit run app.py
```
브라우저에서 http://localhost:8501 접속.

채팅창에 아이디어를 자연어로 입력하면 단계별 진행 상황과 함께 결과 리포트가 출력됩니다.

### FastAPI 백엔드
```bash
uvicorn backend.main:app --reload --port 8000
```

주요 엔드포인트:
- `POST /v1/analyze` → 최종 분석 리포트 JSON
- `POST /v1/analyze/stream` → 단계별 진행 이벤트 스트림(SSE)
- `GET /health` → 헬스체크

예시 입력:
- `음성으로 집 안의 조명과 에어컨을 제어하는 스마트홈 시스템`
- `AI로 옷차림을 분석해 코디를 추천해주는 스마트 거울`

### Next.js 연동 힌트
- FE는 아이디어 텍스트를 `POST /v1/analyze`로 보내 최종 리포트를 받습니다.
- 진행률 UI가 필요하면 `POST /v1/analyze/stream` 응답을 스트리밍으로 읽어 단계별 상태를 표시합니다.

### 코드에서 직접 호출
```python
from dotenv import load_dotenv
load_dotenv()

from agent.graph import agent

result = agent.invoke({
    "user_idea": "음성으로 조명을 제어하는 스마트홈",
    "keywords": [], "patents": [], "ranked_patents": [],
    "report": "", "messages": [], "error": None,
})

print(result["report"])
```

## 프로젝트 구조

```
patentsense/
├── agent/
│   ├── __init__.py
│   ├── graph.py         # LangGraph 워크플로 (4 노드)
│   └── prompts.py       # LLM 프롬프트
├── tools/
│   ├── __init__.py
│   └── kipris.py        # KIPRIS Open API 래퍼
├── app.py               # Streamlit UI
├── requirements.txt
├── .env.example         # API 키 템플릿
├── .gitignore
└── README.md
```

## LangGraph 노드 구성

| 노드 | 역할 |
|---|---|
| `extract_keywords` | Solar LLM으로 아이디어에서 핵심 키워드 추출 |
| `search_patents` | KIPRIS `getWordSearch` 호출, 키워드별 결과 병합 |
| `rank_by_similarity` | Solar 임베딩으로 코사인 유사도 계산, Top 5 |
| `generate_report` | 유사도/등급/표 포함 마크다운 리포트 생성 |

## API 정보

### KIPRIS Plus
- Base URL: `http://plus.kipris.or.kr/kipo-api/kipi`
- 서비스: `patUtiModInfoSearchSevice`
- 메서드: `getWordSearch` (키워드 검색), `getBibliographyDetailInfoSearch` (출원번호 상세조회)
- 인증: `ServiceKey` 쿼리 파라미터

### Solar (Upstage)
- Base URL: `https://api.upstage.ai/v1`
- 모델:
  - `solar-pro` (LLM, 키워드 추출 + 리포트 생성)
  - `embedding-query` (사용자 아이디어 임베딩)
  - `embedding-passage` (특허 문서 임베딩)

## 트러블슈팅

### KIPRIS 호출 시 302 리다이렉트
- `code400.jsp`로 리다이렉트되면 키 미활성화 또는 잘못된 엔드포인트
- KIPRIS Plus **마이페이지 > API KEY 관리**에서 키 재확인
- 신청한 서비스가 **사용중** 상태인지 확인

### `NameError: name 'model' is not defined`
- `agent/graph.py` 95줄 임베딩 호출부 확인 (`model="embedding-query"` 형태여야 함)

### Streamlit이 자동으로 안 열릴 때
- 직접 브라우저에서 http://localhost:8501 접속

## 라이선스

내부 학습/시연용 프로젝트.
