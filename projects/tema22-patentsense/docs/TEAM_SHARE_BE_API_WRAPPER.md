# PatentSense BE API Wrapper 공유

## 이번에 한 일
- `patentsense-` repo에서 `feat/agent-api-wrapper` 브랜치 생성
- 기존 LangGraph 에이전트 로직을 그대로 감싸는 FastAPI 백엔드 추가
- 아이디어 텍스트 입력 → 분석 리포트 반환 API 구현
- 분석 단계별 진행상황을 SSE 스트림으로 전달하는 엔드포인트 추가
- Next.js 마이그레이션을 고려해 CORS 설정과 실행 방법 정리
- README에 백엔드 실행법과 연동 힌트 추가

## 추가된 API
- `POST /v1/analyze`
  - 입력: `idea_text`
  - 출력: 최종 분석 리포트 JSON
- `POST /v1/analyze/stream`
  - 입력: `idea_text`
  - 출력: `queued → keywords → search → rank → conflict → differentiators → report → done` 식의 진행 이벤트
- `GET /health`

## 구현 방향
- 분석 핵심은 기존 `agent/graph.py` 재사용
- 백엔드는 얇은 래퍼 역할만 수행
- 프론트는 다음 단계에서 이 API만 붙이면 됨

## 메모
- 현재는 MVP라서 인메모리/동기 스트리밍 형태
- Next.js 붙일 때는 스트림 소비 방식만 정하면 바로 연결 가능
- 추후 필요하면 job queue / DB / WebSocket으로 확장 가능
