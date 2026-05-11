# 모닝 브리핑 — Frontend (Streamlit)

기획서 §5 MVP의 프론트엔드. 사이드바에서 위치/카테고리를 입력하면 백엔드 `/api/v1/briefing`을 호출해 통합 카드를 표시합니다.

## 빠른 실행

### 로컬 개발

```powershell
# 1) 백엔드를 다른 터미널에서 띄웁니다.
cd ../backend
uv sync
uv run uvicorn app.main:app --reload --port 8001

# 2) 프론트엔드.
uv sync
uv run streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8002` 접속.

### 컨테이너 실행 (전체 통합)

저장소 루트에서:

```powershell
docker compose up --build
```

백엔드(8001) + 프론트엔드(8002)가 같은 도커 네트워크에서 뜨고, 프론트는 `BACKEND_URL=http://backend:8001`로 자동 연결됩니다.

## 개발 모드 (Mock)

날씨/뉴스 에이전트가 미완성인 동안에도 화면을 끝까지 개발할 수 있도록 사이드바에 **"Mock 응답 사용"** 토글이 있습니다.

5가지 시나리오로 `degraded` 분기를 모두 검증할 수 있습니다.

| 시나리오 | 화면 동작 |
|---|---|
| 정상 | 통합 카드 + 날씨 + 뉴스 탭 |
| 날씨 실패 | 좌측 날씨 영역에 안내 문구 |
| 뉴스 실패 | 우측 뉴스 영역에 안내 문구 |
| 둘 다 실패 | 양쪽 안내 + action_tip 비어있음 |
| LLM 실패 | action_tip 비어있고 통합 요약은 폴백 텍스트 |

## 디렉토리

```
frontend/
├── streamlit_app.py            # Streamlit 진입점
├── app/
│   ├── api_client.py           # 백엔드 호출 + 도메인 예외
│   ├── config.py               # BACKEND_URL, 타임아웃
│   ├── constants.py            # 도시/카테고리 옵션
│   ├── mock_data.py            # 5가지 시나리오 mock
│   ├── schemas.py              # 백엔드 contract 미러링
│   └── components/
│       └── briefing_view.py    # 카드 UI 렌더 함수
├── .streamlit/config.toml      # 포트 8002
├── Dockerfile
└── pyproject.toml              # uv
```

## 백엔드 contract

`backend/app/schemas/briefing.py`의 `BriefingRequest` / `BriefingResponse`를 그대로 미러링합니다(`app/schemas.py`). 백엔드 schemas가 변경되면 이 파일도 함께 갱신해야 합니다.

`length`는 기획서에서 짧게/보통/자세히 옵션이 명시되어 있지만 MVP 데모 단순화를 위해 FE에서는 `medium` 고정으로 송신합니다(`app/constants.py`의 `DEFAULT_LENGTH`).

## 합의 필요 항목

- **도시 옵션** → 날씨 에이전트가 OpenWeatherMap에 매핑할 때 인식되는지 확인.
- **카테고리 옵션** → 뉴스 에이전트의 NewsAPI/네이버 카테고리 매핑 테이블과 일치 여부 확인.

## 데모 동선 (기획서 §2 페르소나 기준)

1. **첫 방문**: 사이드바 폼이 비어있는 상태에서 위치/카테고리 입력 → "브리핑 생성".
2. **재방문(F5)**: 저장된 설정이 자동 복원되며 즉시 카드가 표시됨 (LocalStorage).
3. **시나리오 변경**: 카테고리를 추가/제거 후 "브리핑 생성"으로 즉시 반영.
4. **재호출**: 메인 카드 우상단 "다시 생성" 버튼.
5. **초기화**: 사이드바 "설정 초기화"로 첫 방문 상태로 복귀.
