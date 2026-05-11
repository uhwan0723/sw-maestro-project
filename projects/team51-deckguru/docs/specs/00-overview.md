# 00. 프로젝트 개요 — DeckGuru

## 1. 한 줄 정의

롤토체스(TFT) 유저의 **티어 + 선호 스타일 + 자연어 질문**을 입력받아, **현재 패치 기준 덱 추천 + 운영법 + 출처 + 확신도**를 산출하는 RAG 기반 Agentic AI 서비스.

## 2. 설계 철학

본 프로젝트는 "AI native 개발"을 지향한다. 모든 Agent 출력은 **검증 가능 / 재현 가능 / 출처 추적 가능**해야 한다.

### 2.1 Grounding-First (가장 중요)

기획서가 핵심 위험으로 식별한 "환각 가능성"(§1.4)에 대한 시스템 차원 대응:

| 원칙 | 구현 |
|---|---|
| **이름 화이트리스트** | 응답의 `core_units`, `key_items`, `traits`, `augments`는 RAG 인덱스의 `name` 집합에 존재해야 한다. 미존재 항목은 deterministic post-processor가 제거. |
| **수치 인용 제한** | 응답에 등장하는 수치(승률·평균등수 등)는 `evidence_quotes[]`에 동일 수치가 있을 때만 허용. 없으면 정성 표현으로 변환("높은 편"). |
| **출처 1:1 대응** | 외부에서 인용한 모든 주장은 `sources[]` 항목과 1:1 매핑. 매핑 실패 → `confidence` 강등. |
| **금지 표현 필터** | "1등 보장", "승률 100%", "무조건" 등의 단정 표현은 정규식 필터 + LLM 재작성. |

### 2.2 Patch-Versioned Data

기획서가 언급한 "예전에 좋았던 덱이 현재도 좋은지 판단 어려움"(§1.4)에 대한 대응:

- 모든 RAG chunk는 `patch_version` 메타데이터를 갖는다.
- 검색 시 `where={"patch_version": current_patch}` 필터링 강제.
- 응답 헤더에 `patch_version`을 항상 포함. UI 상단에 항상 노출.
- 패치 직후 데이터 부족 시 `warnings[]`에 `"insufficient_data_after_patch"` 표시.

### 2.3 결정성 (Determinism)

- LLM 호출은 `temperature=0`, `top_p=1`, structured output (JSON schema enforced).
- 검색 → 검증 → 포맷팅은 모두 **순수 함수**. LLM은 자연어화에만 사용.
- 동일 입력 + 동일 RAG state → 동일 응답.

### 2.4 명시적 제외 영역 (Out-of-Scope)

| 제외 항목 | 이유 |
|---|---|
| LoL / FC 온라인 등 다른 게임 지원 | MVP 범위 집중 (기획서 §5.2.2) |
| 사용자 전적 연동 (Riot API) | 인증/법적 검토 필요. v2로 백로그 |
| 자동 플레이 / 매크로 | 서비스 목적과 불일치 |
| "이 덱 가면 무조건 1등" 같은 보장 | 환각·과장 위험 |
| 멀티턴 대화 (후속 질문 메모리) | MVP 안정성 우선. 단발 추천만 |
| 사용자 계정 / 장기 개인화 | MVP는 세션 단위 익명 |
| 실시간 통계 사이트 완전 연동 | API 제한 / 크롤링 ToS 검토 부족 |

### 2.5 자유 입력 vs 표준 인텐트

자연어 질문은 4개 표준 인텐트로 분류 (`02-agent-strategy-spec.md` §3 참조):

```
recommend_deck | deck_playstyle | item_pivot | patch_summary | other
```

`other`는 "지원 범위 안내" 응답으로 직행 (LLM 호출 절약).

## 3. MVP 범위

### 포함 (4/29 ~ 5/9)

- 롤토체스 단일 게임 지원
- 4가지 인텐트(추천덱 / 운영법 / 아이템 기반 / 패치 요약) 처리
- LangGraph 기반 순차 워크플로우 + (조건부) Live Research ReAct 루프
- RAG: 기물 / 특성 / 아이템 / 증강체 / 덱 템플릿 / 패치 요약 / 기본 운영 / 용어 사전 (8개 인덱스)
- 출처 + 확신도 + 패치 버전 표시
- 캐싱 (L1 in-memory + L2 SQLite, patch 키)
- 결과 카드 UI (Next.js + Motion)

### 제외

- 위 §2.4 전체
- 학습 / 파인튜닝 (모든 추론은 zero-shot + RAG)
- 실시간 스트리밍 (단일 요청-응답)

## 4. 대상 사용자

기획서 §1.5 그대로 + 우선순위:

| 우선순위 | 사용자 | 핵심 니즈 |
|---|---|---|
| P0 | 티어 상승을 원하는 골드~플래티넘 유저 | 현재 패치에서 점수 올리기 좋은 덱 + 쉬운 운영 |
| P0 | 패치 후 복귀 유저 | 이번 패치 메타 변경점 + 추천 덱 |
| P1 | 초보 유저 | 어려운 용어 풀어 설명 + 쉬운 덱 |
| P1 | 공략 탐색 시간 부족한 유저 | 여러 출처 종합 요약 |
| P2 | 프로젝트 평가자 | Agentic Workflow + RAG 과정의 가시성 |

## 5. 핵심 가치 (기획서 §1.6 정합)

| 가치 | 시스템 차원 보장 |
|---|---|
| 최신성 | patch_version 1급 메타 + UI 상단 노출 |
| 근거성 | 모든 외부 인용은 `sources[]`에 URL+제목+발행일 |
| 개인화 | tier + play_style → 추천 후보 필터링 + rationale |
| 실행 가능성 | 모든 추천은 phase별 (early/mid/late) 운영 절차 동반 |
| 신뢰성 | confidence (high/medium/low) + warnings[] 명시 |

## 6. 성공 지표 (KPI)

기획서 §5.1을 측정 가능한 형태로 보강:

| 지표 | 정의 | 측정 방법 | 목표 |
|---|---|---|---|
| Schema Pass Rate | LLM 응답이 `RecommendationResponse` 검증 통과한 비율 | 서버 로그 | ≥ 98% |
| Grounding Pass Rate | 응답 고유명사가 화이트리스트에 100% 매칭된 비율 | 자동 평가 | ≥ 95% |
| Source Coverage | 응답의 외부 인용 사실 중 `sources[]` 매핑된 비율 | 자동 평가 | 100% |
| Intent Accuracy | 골드셋 20개 질문의 `intent` 정확도 | `evals/golden_set.jsonl` | ≥ 90% |
| Latency P50 / P95 | 업로드 → 결과 표시 | 클라이언트 + 서버 | ≤ 15s / ≤ 30s |
| Cache Hit Rate | 동일 정규화 질문 재호출 캐시 hit 비율 | 서버 로그 | ≥ 30% (데모 시) |
| User Satisfaction | 팀 내부 5점 평균 | 정성 평가 (3인 이상) | ≥ 4.0 |

## 7. 팀 구성 (5인)

| 역할 | 인원 | 책임 문서 |
|---|---|---|
| Strategy Agent (오케스트레이션 / 프롬프트) | 1 | `02-agent-strategy-spec.md` |
| RAG Agent (인덱스 / 임베딩 / 검색) | 1 | `03-agent-rag-spec.md` |
| Research Agent (외부 수집 / 도구) | 1 | `04-agent-research-spec.md` |
| Backend | 1 | `05-backend-spec.md` |
| Frontend | 1 | `06-frontend-spec.md` |

상세 협업 인터페이스는 `08-roles-and-handoffs.md` 참조.

## 8. 문서 맵

```
docs/specs/
├── README.md
├── 00-overview.md                  # 본 문서
├── 01-architecture.md              # 시스템 아키텍처
├── 02-agent-strategy-spec.md       # Strategy Agent (LangGraph 오케스트레이션)
├── 03-agent-rag-spec.md            # RAG (인덱싱·검색·grounding)
├── 04-agent-research-spec.md       # Live Research (외부 정보 수집)
├── 05-backend-spec.md              # FastAPI Gateway
├── 06-frontend-spec.md             # Next.js UI
├── 07-data-contracts.md            # JSON 스키마 / API 계약 (단일 진실 소스)
└── 08-roles-and-handoffs.md        # 역할 분담 / 인터페이스 / 마일스톤
```

## 9. 기획서 피드백 (전체 시스템 차원)

| # | 기획서 표현 | 문제 | 본 spec의 보정 |
|---|---|---|---|
| 1 | "Agentic AI" + "싱글 에이전트" (§2.2) 동시 사용 | 진짜 ReAct 루프인지 순차 워크플로우인지 모호 | LangGraph **순차 노드 파이프라인** + **조건부 ReAct 분기**(Live Research에 한정)로 명확화 |
| 2 | "RAG로 환각 방지" (§1.4) | RAG는 환각을 *줄일* 뿐이다 | §2.1에 화이트리스트·수치 필터·금지 표현 등 다층 grounding 강제 |
| 3 | "최신성"이 핵심 가치 vs 일 1회 배치 | 모순 | patch_version 메타 필터링으로 "옛 정보 섞이지 않음"을 최소 보장. UI에 기준 패치 항상 노출 |
| 4 | 평가 지표 모두 정성적 (§5.1) | 측정 불가 | §6에 자동 골든셋 + 측정 임계값 |
| 5 | 데이터 소스 ToS / 저작권 미검토 | 법적 위험 | `04-agent-research-spec.md` §7에 화이트리스트 도메인 + robots.txt 검토 |
| 6 | LLM 모델·비용 미명시 | 합의 부재 시 일정 위험 | `08-roles-and-handoffs.md` §3에 4/29 합의 마일스톤 |
| 7 | 응답 스키마 부재 | 3명 병렬 작업 불가 | `07-data-contracts.md`를 단일 진실 소스로 못박음 |
| 8 | "30초 이내 응답" | percentile 미지정 | §6에 P50/P95 분리 |
| 9 | 사용자 피드백 분석 부재 | 데모 후 학습 루프 없음 | `05-backend-spec.md` §3.4에 `/feedback` + JSONL 보관 |
