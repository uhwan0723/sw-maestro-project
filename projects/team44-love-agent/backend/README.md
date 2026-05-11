# Backend

FastAPI 단일 서버로 프론트엔드 상담 요청을 받고, LangGraph 기반 에이전트 워크플로우를 실행한 뒤 상담 상태·부분 결과·최종 결과를 반환하는 API 영역입니다.

## 담당자

- 주 담당: 김민우
- 프로토콜 검토: 신현성
- 프론트엔드 연동 확인: 김준서, 박준혁

## 구현 결정

- 서버는 **FastAPI 단일 프로세스**로 진행합니다.
- 워크플로우 orchestration은 **LangGraph**로 구성합니다.
- 상담 상태는 `consultation_id` 기준 **in-memory store**에 분리 저장합니다.
- 프론트의 실시간 진행 표시를 위해 **SSE(Server-Sent Events)** 로 `StreamEvent`를 발행합니다.
- DB 저장, 사용자 인증, 영속 LangGraph checkpoint는 현재 구현 범위에서 제외합니다.

## 담당 범위

- `POST /consultations` 상담 시작 API
- `GET /consultations/{consultation_id}` 현재/최종 상담 결과 조회 API
- `GET /consultations/{consultation_id}/events` SSE 스트리밍 API
- Pydantic 요청/응답 모델과 `agents/workflows/message_schema.md` 계약 정렬
- LangGraph 노드/엣지 구성과 라운드별 실행 연결
- `consultation_id`별 in-memory 상태 저장 및 이벤트 큐 관리
- 오류, 재시도, 스킵, 조기 종료 흐름

## 작업 기준

- 김민우는 백엔드가 에이전트 실행 골격과 자연스럽게 연결되도록 구조를 잡습니다.
- 신현성은 API 요청/응답이 프로토콜과 메시지 스키마를 지키는지 검토합니다.
- 김준서는 화면 표시를 위해 필요한 응답 필드와 SSE 이벤트 소비 방식을 요청합니다.
- 박준혁은 응답 상태에 따라 사용자에게 보여줄 문구 key가 충분한지 확인합니다.
- API 응답 구조가 바뀌면 `frontend/`, `agents/workflows/`, `docs/team44-love-agent/03_features_workflow/user_messages.md` 문서도 함께 확인합니다.
- 백엔드는 한국어 사용자 노출 문구를 직접 만들지 않고 `*_user_message_key`만 반환합니다.

## API 초안

| Method | Path | 역할 | 응답 |
| --- | --- | --- | --- |
| `GET` | `/health` | 서버 상태 확인 | `{ "status": "ok" }` |
| `POST` | `/consultations` | `UserConsultationRequest` 검증 후 상담 워크플로우 시작 | `{ "consultation_id": string, "status": "pending" }` |
| `GET` | `/consultations/{consultation_id}` | 현재까지의 상태 또는 최종 `ConsultationResponse` 조회 | `ConsultationResponse` |
| `GET` | `/consultations/{consultation_id}/events` | 진행 상태, 에이전트 발언, 오류, 완료 이벤트 SSE 스트림 | `StreamEvent` sequence |

## 향후 폴더 배치 기준

```text
backend/
├── app/
│   ├── main.py                  # FastAPI app 생성, 라우터 등록
│   ├── api/
│   │   ├── consultations.py     # POST/GET 상담 API
│   │   └── events.py            # SSE endpoint
│   ├── schemas/
│   │   ├── consultation.py      # Pydantic 요청/응답 모델
│   │   └── events.py            # StreamEvent 모델
│   ├── workflow/
│   │   ├── graph.py             # LangGraph topology/conditional edges
│   │   ├── nodes.py             # supervisor/agent node 구현
│   │   └── state.py             # ConsultationState reducer/helper
│   ├── store/
│   │   └── memory.py            # consultation_id별 in-memory state
│   ├── services/
│   │   ├── event_broker.py      # SSE event queue/pub-sub
│   │   └── llm_client.py        # LLM 호출 adapter 또는 mock
│   └── errors.py                # 예외와 PublicError 변환
├── tests/
└── README.md
```

## 구현 검증 기준

- FastAPI 앱이 로컬에서 부팅된다.
- `POST /consultations`가 스키마를 검증하고 `consultation_id`별 상태를 만든다.
- LangGraph mock workflow가 `ConsultationStatus` 순서대로 상태를 전이한다.
- SSE가 `status_changed`, `agent_message_added`, `completed` 이벤트를 순서대로 보낸다.
- `GET /consultations/{consultation_id}`가 `ConsultationResponse` 형태만 반환한다.
- `PublicError.user_message_key`, `PublicTermination.user_message_key`는 `user_messages.md`의 key만 사용한다.

## 로컬 실행

```powershell
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH='backend'
$env:LLM_PROVIDER='mock'
python -m uvicorn app.main:app --reload
```

기본값은 `LLM_PROVIDER=mock`입니다. Upstage를 실제로 호출하려면 아래 환경 변수를 설정합니다.

```powershell
$env:LLM_PROVIDER='upstage'
$env:UPSTAGE_API_KEY='<your-upstage-api-key>'
$env:UPSTAGE_BASE_URL='https://api.upstage.ai/v1'
$env:UPSTAGE_MODEL='solar-pro3'
```

## Docker 실행

루트 디렉터리에서 실행합니다.

```powershell
docker compose up --build backend
```

확인:

```powershell
curl http://localhost:8000/health
```

Mock이 아닌 Upstage로 실행하려면 shell 환경 변수만 바꿉니다. `.env` 파일은 커밋하지 않습니다.

```powershell
$env:LLM_PROVIDER='upstage'
$env:UPSTAGE_API_KEY='<your-upstage-api-key>'
docker compose up --build backend
```

현재 SSE는 기존 MD 계약대로 workflow progress event만 보냅니다. Upstage token streaming은 포함하지 않습니다.
