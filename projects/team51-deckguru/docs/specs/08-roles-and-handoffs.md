# 08. Roles & Handoffs — 역할 분담 / 인터페이스 / 마일스톤

> 5인 팀의 책임 경계, 인터페이스 합의, 마일스톤, 의사결정 프로토콜.
> 본 문서는 일정과 의존성을 단일 진실 소스로 관리한다.

---

## 1. 팀 구성 및 책임 경계

| 역할 | 인원 | 1차 책임 문서 | 핵심 산출물 |
|---|---|---|---|
| **Agent-1: Strategy** | 1 | `02-agent-strategy-spec.md` | LangGraph StateGraph, 7개 노드, prompts, `verify_grounding` |
| **Agent-2: RAG** | 1 | `03-agent-rag-spec.md` | 8개 ChromaDB 인덱스, 빌드 스크립트, `RagService` API |
| **Agent-3: Research** | 1 | `04-agent-research-spec.md` | Live Research sub-graph, 도구 3종, 도메인 화이트리스트 |
| **Backend** | 1 | `05-backend-spec.md` | FastAPI, 캐시, rate limit, 미들웨어, Mock fixture |
| **Frontend** | 1 | `06-frontend-spec.md` | Next.js UI, 입력 폼, 결과 카드, Motion |

### 1.1 공동 책임 (no single owner)

| 항목 | 공동 책임자 |
|---|---|
| `07-data-contracts.md` 변경 | 전원 (PR 리뷰 강제) |
| 골든셋 (`evals/golden_set.jsonl`) | Agent-1 + Agent-2 (작성) / 전원 (검토) |
| 평가 KPI 측정 자동화 | Agent-1 + Backend |
| 데모 시나리오 (5/9) | 전원 |
| README + 환경 변수 docs | Backend (작성) / 전원 (리뷰) |

---

## 2. 인터페이스 합의 (Inter-component contracts)

각 컴포넌트가 호출하는/제공하는 함수 시그니처. 변경 시 양 끝 담당자 합의 필수.

### 2.1 Backend → Strategy Agent

```python
# 02-agent-strategy-spec.md §5
async def run_strategy_agent(
    request_id: str,
    tier: Tier,
    play_style: PlayStyle,
    question: str,
    *,
    patch_version: str,
    timeout_s: float = 25.0,
) -> RecommendationResponse: ...
```

소유: Agent-1. 호출자: Backend.

### 2.2 Strategy Agent → RAG Service

```python
# 03-agent-rag-spec.md §4
class RagService:
    def search(self, index: IndexName, query: str, *, k: int, patch_version: str, where: dict | None = None) -> list[RagChunk]: ...
    def multi_search(self, plan: list[tuple[IndexName, str, int]], *, patch_version: str) -> list[RagChunk]: ...
    def get_whitelist(self, patch_version: str) -> dict[str, set[str]]: ...
```

소유: Agent-2. 호출자: Agent-1, Agent-3.

### 2.3 Strategy Agent → Live Research

```python
# 04-agent-research-spec.md §8
async def run_live_research(
    request_id: str,
    *,
    question: str,
    extracted_keywords: list[str],
    patch_version: str,
    max_steps: int = 5,
    timeout_s: float = 15.0,
) -> ResearchResult: ...
```

소유: Agent-3. 호출자: Agent-1.

### 2.4 Frontend → Backend

`07-data-contracts.md` §5의 5개 엔드포인트.
소유: Backend. 호출자: Frontend.

### 2.5 의존 그래프

```
Frontend ──HTTP──▶ Backend ──function──▶ Strategy Agent ──function──▶ RagService
                                                       │              ▲
                                                       └──function──▶ Live Research ──function (whitelist)──┘
```

**병렬 가능성 분석:**
- Day 1 (4/29): 5명 모두 독립적으로 시작 가능 (계약 합의만 끝나면)
- Day 2 (4/30): Backend가 Mock fixture 제공 → Frontend 병렬 가능
- Day 4~6 (5/4~6): RAG → Strategy → Live Research → Backend 통합 (직렬)

---

## 3. 사전 결정 사항 (Day 1, 4/29 마감)

다음 항목은 **4/29 17:00까지 결정**되어야 한다. 미결정 시 후속 일정 전체 위험.

| # | 항목 | 결정자 | 영향 받는 spec |
|---|---|---|---|
| D1 | LLM 모델 (recommend / analyze_meta) | 전원 (비용/성능 trade-off) | 02, 05 |
| D2 | LLM 모델 (analyze_intent / reflect 등 cheap) | 전원 | 02, 04 |
| D3 | 임베딩 모델 (bge-m3 vs e5-large) | Agent-2 | 03 |
| D4 | Tavily API key 발급 또는 DDG fallback | Agent-3 | 04 |
| D5 | 도메인 화이트리스트 5개 + 유튜브 채널 3~5개 | Agent-3 + 전원 | 04 |
| D6 | lolchess.gg / tactics.tools / metatft.com ToS 검토 | Agent-3 | 04 |
| D7 | 응답 스키마 (`RecommendationResponse`) Pydantic 1차 머지 | 전원 | 07 |
| D8 | Mock fixture JSON 1개 (recommend_deck/gold/stable) | Backend + Agent-1 | 05, 06 |
| D9 | 호스팅 (fly.io / Railway / 데모 PC) 1순위 + 폴백 | Backend | 05 |
| D10 | LangGraph 0.2+ pin / Python 3.11 pin | Backend | 모두 |

각 결정 사항은 `docs/decisions/D<번호>_<요약>.md`에 1페이지 ADR로 기록.

---

## 4. 마일스톤 (4/29 ~ 5/9, 11일)

기획서 §5.3을 압축 + 병렬화 강제. **각 셀은 "당일 EOD 산출물"** 이다.

| 날짜 | Agent-1 (Strategy) | Agent-2 (RAG) | Agent-3 (Research) | Backend | Frontend |
|---|---|---|---|---|---|
| **4/29** Day 1 | 인텐트 분류 few-shot v0 + LangGraph skeleton | 8개 인덱스 schema 확정 + ingest 스크립트 뼈대 | 도메인 화이트리스트 + ToS 검토 결과 | API 계약 v0 (07-data-contracts 기준) | 와이어프레임 + Tailwind 셋업 |
| **4/30** Day 2 | Strategy `analyze_intent` 노드 동작 | 정적 데이터 1차 수집 (units/items) | 도구 3종 단위 함수 동작 | FastAPI skeleton + Mock `/api/recommend` | Next.js skeleton + Mock 응답 연동 + 폼 UI |
| **5/1** Day 3 | `recommend` 노드 prompt v1 + LLM 호출 | 8개 인덱스 모두 수집 + chunking | Live Research ReAct 루프 1회 동작 | 캐시 + rate limit + 미들웨어 | DeckCard 컴포넌트 |
| **5/2** Day 4 | `verify_grounding` 결정적 룰 | 임베딩 + ChromaDB upsert | extract_facts LLM | 에러 매핑 + structlog | SourcesPanel + WarningsPanel |
| **5/3** Day 5 | `analyze_meta` + structured output | 검색 API + whitelist API | 캐시(7d) + promotion queue | Agent 통합 (Mock 제거) | Motion + LoadingStages |
| **5/4** Day 6 | 통합 테스트 (RAG + Strategy 직결) | RAG eval (Recall@3, MRR) | Research eval (트리거 정확도) | Backend e2e (실 Agent) | Confidence/Patch 배너 |
| **5/5** Day 7 | 프롬프트 튜닝 (golden set 90%) | 패치 14.9 데이터 최종 갱신 | 화이트리스트 폴리싱 + robots.txt 캐시 | 통합 latency 측정 | About / Demo 페이지 |
| **5/6** Day 8 | E2E 시나리오 통과 (3개 골든) | (지원) | (지원) | 캐시 워밍 + DEMO_MODE | 에러 UI + 접근성 |
| **5/7** Day 9 | 환각 방지 룰 폴리싱 | 패치 변경 대비 rollback 절차 | 백업 (Tavily 다운 시) | 클라우드 1차 배포 또는 데모 PC 확정 | UI 폴리싱 |
| **5/8** Day 10 | (전원 합동) E2E 리허설 + 골든셋 통과 + 캐시 워밍 |
| **5/9** Day 11 | 데모 발표 + 영상 + README 마감 |

### 4.1 Critical Path

```
RAG 인덱싱 완료 (5/2) → Strategy 통합 (5/4) → E2E 안정화 (5/6) → 캐시 워밍 (5/8)
```

병목 1순위는 **RAG 데이터 품질**. Agent-2가 늦어지면 Agent-1이 무엇을 검색해야 할지 정해지지 않음. → 5/1까지 데이터 수집을 마쳐야 후속 작업 가능.

### 4.2 폴백 시나리오

| 위험 | Trigger | 폴백 |
|---|---|---|
| RAG 데이터 부족 | 5/2 EOD까지 5개 미만 인덱스 완성 | deck_templates / units / items / patch_summary 4개로 축소. 나머지는 데모 미사용 |
| Live Research 불안정 | 5/5까지 ReAct 1회도 성공 안 됨 | `need_live=False` 강제 (env flag). Strategy는 RAG only로 작동 |
| 클라우드 배포 실패 | 5/7까지 배포 미완 | 데모 PC + ngrok / Cloudflare Tunnel |
| LLM API 사고 | 5/9 데모 직전 | 캐시된 3개 골든 시나리오로 대응 (`/demo` 페이지) |

---

## 5. 의사결정 프로토콜

### 5.1 일상 결정 (변경 영향 단일 컴포넌트)

해당 담당자가 결정. PR 1개로 머지.

### 5.2 인터페이스 변경 (2개 이상 컴포넌트 영향)

1. 제안자가 해당 spec 파일에 변경 PR 작성
2. 영향 받는 담당자 모두 reviewer로 지정 (CODEOWNERS)
3. 모두 approve 후 머지
4. 머지 후 24시간 내 양 컴포넌트 코드 PR

### 5.3 Schema 변경 (`07-data-contracts.md`)

위 5.2 + 다음 추가:
- `tests/fixtures/contract_examples/`에 새/변경 fixture 동봉
- CI의 `test_contracts.py` 통과
- 호환성 매트릭스(`07-data-contracts.md` §6.2) 표시

### 5.4 Out-of-spec 결정 (시간 부족)

표준 절차를 따를 시간이 없을 때:
1. Slack에 `@here #51조 [URGENT]` 메시지 + 1~2문장 결정안
2. 30분 내 반대 없으면 진행
3. 24h 내 ADR 또는 spec PR로 사후 기록

---

## 6. 일일 리듬 (Day 1~10)

매일 동일한 패턴.

| 시간 | 활동 |
|---|---|
| 10:00 | 스탠드업 (15min). 어제 산출물 / 오늘 계획 / 블로커 |
| 10:15 ~ 18:00 | 작업 |
| 18:00 | EOD 체크인 (15min). 마일스톤 표의 산출물 달성 여부 확인. 미달성 시 폴백 결정. |

스탠드업/EOD는 비동기(노션/슬랙)로도 OK. 단, EOD에 마일스톤 cell 미달성이면 **반드시** 폴백 결정 후 잠.

---

## 7. 코드 리뷰 / 머지 룰

| 변경 종류 | 리뷰어 |
|---|---|
| 단일 컴포넌트 내부 | 동료 1명 |
| 인터페이스 (function signature 변경) | 양 끝 담당자 + 1명 |
| `07-data-contracts.md` | 전원 |
| 프롬프트 변경 | Agent-1 + 1명 (회귀 위험) |
| 화이트리스트 변경 | Agent-3 + Agent-2 |

**Force-merge 금지.** CI 빨간불 머지 금지.

---

## 8. 평가 / KPI 측정 책임

| KPI (00-overview §6) | 측정 코드 | 책임자 |
|---|---|---|
| Schema Pass Rate | `evals/run_evals.py` | Agent-1 |
| Grounding Pass Rate | `evals/run_evals.py` | Agent-1 |
| Source Coverage | `evals/run_evals.py` | Agent-1 |
| Intent Accuracy | `evals/run_evals.py` | Agent-1 |
| Latency P50/P95 | Backend 로그 분석 | Backend |
| Cache Hit Rate | Backend `/api/_internal/cache-stats` | Backend |
| User Satisfaction | 정성 평가 (3인 이상) | 전원 |
| RAG Recall@3 / MRR | `evals/rag_eval.jsonl` | Agent-2 |
| Live trigger 정확도 | `evals/research_eval.jsonl` | Agent-3 |

CI에서 `Schema Pass Rate < 95%`면 fail. 다른 KPI는 PR comment에 표시만.

---

## 9. 데모 (5/9) 책임 분배

| 항목 | 담당 |
|---|---|
| 발표 자료 (스토리 + 슬라이드) | Frontend (대표) + 전원 검토 |
| 시연 PC 셋업 | Backend |
| 캐시 워밍 (3개 골든 시나리오) | Backend + Agent-1 |
| 라이브 시연 진행 | 1명 (예: Frontend) |
| 시연 영상 녹화 (백업) | Frontend |
| Q&A 대응 | 전원 (질문 도메인별 분담) |
| README 마감 | Backend |

### 9.1 시연 흐름 (10분 가정)

1. (1min) 문제 소개 — 기획서 §1
2. (2min) 시스템 아키텍처 — `01-architecture.md` 그림 1장
3. (5min) 라이브 시연:
   - 시나리오 1 (recommend_deck) — 캐시 hit
   - 시나리오 2 (deck_playstyle) — 캐시 hit
   - 시나리오 3 (item_pivot) — 라이브 호출 (실제 RAG + Live Research)
4. (1min) 환각 방지 / 출처 표시 데모 — verify_grounding로 걸러진 케이스 1개
5. (1min) 한계 + v2 백로그

---

## 10. v2 백로그 (MVP 미포함, 데모 후 정리용)

| 항목 | 출처 |
|---|---|
| 멀티턴 대화 + 후속 질문 메모리 | 기획서 §3.2.1 9번 |
| 사용자 전적 연동 (Riot API) | 기획서 §5.2.2 |
| LoL / FC 온라인 지원 | 기획서 §5.2.2 |
| Promotion Queue 검토 + 자동 인덱싱 | `04` §6 |
| SSE 스트리밍 (실제 진행 상태) | `06` §7.1 |
| `pydantic-to-zod` 자동 schema 동기화 | `07` §6 |
| 사용자 계정 / 장기 개인화 | 기획서 §5.2.2 |
| Riot API 연동 | 기획서 §5.2.2 |
| 비-목표 (전체) 재검토 | `00` §2.4 |

---

## 11. 기획서 피드백 (이 문서가 보정한 부분)

| # | 기획서 | 문제 | 본 spec |
|---|---|---|---|
| 1 | "기획자 5인" 명단만 있음 (§참여자) | 역할 분담 X | §1에 5개 역할 명시 |
| 2 | 일정(§5.3) 7단계 한 차원 | 누가/어떤 의존성으로 병렬인지 불명 | §4 일별 × 5인 매트릭스 |
| 3 | Critical path 분석 부재 | 일정 risk 가시화 X | §4.1, §4.2 폴백 시나리오 |
| 4 | 의사결정 프로토콜 부재 | 충돌 시 마비 | §5 + ADR 디렉토리 |
| 5 | 인터페이스 합의 시점 미정 | 후반에 통합 폭발 위험 | §3 D1~D10 4/29 마감 |
| 6 | 평가 책임자 미정 | KPI 측정 누락 위험 | §8 KPI별 owner |
| 7 | 데모 진행 책임 미정 | 5/9 즉흥 진행 위험 | §9 분배 + 흐름 |
| 8 | v2 백로그 부재 | 데모 후 다음 단계 모호 | §10 |
