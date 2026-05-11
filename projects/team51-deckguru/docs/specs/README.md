# DeckGuru Specs

DeckGuru의 제품, 아키텍처, Agent, Backend, Frontend, API 계약 사양을 모아 둔 디렉토리입니다.

처음 읽는다면 아래 순서로 확인하세요.

| 순서 | 문서 | 목적 |
| --- | --- | --- |
| 1 | [`00-overview.md`](./00-overview.md) | 제품 목표, 설계 원칙, MVP 범위 확인 |
| 2 | [`01-architecture.md`](./01-architecture.md) | 전체 시스템 구조 확인 |
| 3 | [`07-data-contracts.md`](./07-data-contracts.md) | API와 데이터 schema 확인 |
| 4 | [`08-roles-and-handoffs.md`](./08-roles-and-handoffs.md) | 역할 분담과 handoff 확인 |
| 5 | [`02-agent-strategy-spec.md`](./02-agent-strategy-spec.md) | Strategy Agent 흐름과 grounding 정책 확인 |
| 6 | [`03-agent-rag-spec.md`](./03-agent-rag-spec.md) | RAG 인덱스, chunk, 검색 계약 확인 |
| 7 | [`04-agent-research-spec.md`](./04-agent-research-spec.md) | Live Research 도구와 promotion queue 확인 |
| 8 | [`05-backend-spec.md`](./05-backend-spec.md) | FastAPI gateway, cache, API 정책 확인 |
| 9 | [`06-frontend-spec.md`](./06-frontend-spec.md) | Next.js UI, 상태, API 연결 정책 확인 |

실행 방법과 현재 구현 상태는 루트 [`README.md`](../../README.md), 백엔드는 [`backend/README.md`](../../backend/README.md), 프론트엔드는 [`frontend/README.md`](../../frontend/README.md)를 우선 확인하세요.
