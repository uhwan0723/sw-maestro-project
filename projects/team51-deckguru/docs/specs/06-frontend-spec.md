# 06. Frontend — Next.js Web UI

> 담당: Frontend
> 범위: Next.js 페이지/컴포넌트, 입력 폼, 결과 카드, Motion 인터랙션, 로딩/에러 UX, 상태 관리, 접근성, 데모 시나리오
> 의존:
> - `05-backend-spec.md` (`POST /api/recommend` 등)
> - `07-data-contracts.md` (`RecommendationResponse` Zod schema)

---

## 1. 책임 범위

| 포함 | 제외 |
|---|---|
| Next.js 14 App Router 페이지 | 백엔드 API |
| 입력 폼 (티어 / 스타일 / 질문 / 예시 칩) | LLM 프롬프트 |
| 결과 카드 (덱 / 운영법 / 출처 / 확신도) | RAG / DB |
| Motion 애니메이션 (로딩 단계, 카드 등장) | 사용자 인증 |
| 에러/로딩/타임아웃 UX | 분석 대시보드 |
| 반응형 (가로 360px 이상) | 다국어 (한국어 only) |
| Zod 런타임 검증 | API 키 / 외부 호출 |

---

## 2. 기술 스택

| 도구 | 용도 |
|---|---|
| Next.js 14+ (App Router) | 라우팅, RSC, fetch |
| TypeScript 5+ | 타입 안정성 |
| Tailwind CSS + shadcn/ui | 스타일링 |
| framer-motion | 로딩 단계, 카드 등장, 화면 전환 |
| Zustand | 폼 상태 + 마지막 응답 |
| Zod | 런타임 응답 검증 (07-data-contracts와 1:1) |
| `pretendard` (web font) | 한국어 본문 |
| `lucide-react` | 아이콘 |

> **결정 사항** — 기획서가 "Axios 또는 Fetch", "Zustand 또는 Context"로 둘 다 열어둠. 본 spec은 **fetch + Zustand**로 못박는다 (코드 스타일 일관성).

---

## 3. 페이지 구성

| Path | 컴포넌트 | 설명 |
|---|---|---|
| `/` | `<Home />` | 입력 폼 + 결과 패널 (single page experience) |
| `/about` | `<About />` | 서비스 소개, 한계 명시, RAG/Agent 설명 |
| `/demo` | `<Demo />` | 캐시 워밍된 3개 골든 시나리오 빠른 호출 (5/9 발표용) |

> **단일 페이지 unfold** 흐름. 결과는 입력 폼 아래에서 펼쳐진다. 라우트 이동 X (기획서 §3.2.1과 부합).

---

## 4. 컴포넌트 트리

```
<RootLayout>
  ├── <PatchBanner />          # 페이지 mount 시 GET /api/patch-info
  ├── <Home>
  │     ├── <RecommendForm>
  │     │     ├── <TierSelect />
  │     │     ├── <PlayStyleCards />     # 4개 라디오 카드
  │     │     ├── <QuestionTextarea />
  │     │     ├── <ExampleChips />       # GET /api/example-questions
  │     │     └── <SubmitButton />
  │     └── <ResultPanel response={...}>
  │           ├── <MetaSummaryCard />
  │           ├── <ConfidenceBadge />
  │           ├── <DeckCardList>
  │           │     {response.decks.map(d => <DeckCard deck={d} />)}
  │           └── <SourcesPanel />
  │           └── <WarningsPanel />     # warnings 비어있으면 미렌더
  │           └── <FeedbackBar />
  └── <Footer />
```

---

## 5. 입력 폼 (`<RecommendForm />`)

| 필드 | UI | 검증 |
|---|---|---|
| 티어 | shadcn `<Select />` 8개 옵션 | 필수 |
| 선호 플레이 스타일 | 4개 라디오 카드 (아이콘 + 한 줄 설명) | 필수 |
| 자연어 질문 | `<Textarea />` 3줄, 글자수 카운터 (0/500) | 1~500자 |
| 제출 | `<Button>덱 추천 받기</Button>` | 위 3개 미충족 시 disabled |

### 5.1 플레이 스타일 카드

| value | 라벨 | 설명 | 아이콘 |
|---|---|---|---|
| `stable_top4` | 안정적인 순방형 | "꾸준히 4등 안에 들고 싶어요" | `Shield` |
| `high_risk_first` | 고점 높은 1등형 | "1등 노리는 한방 덱 좋아해요" | `Crown` |
| `easy_beginner` | 쉬운 초보자형 | "운영이 단순한 덱이 좋아요" | `Sprout` |
| `flexible` | 유동적인 운영형 | "초반 상황 보고 덱 결정해요" | `Wand2` |

### 5.2 예시 질문 칩

`/api/example-questions`로 받아오는 4개 (intent별 1개). 클릭 시 textarea 채움 + 자동 포커스.

---

## 6. 결과 화면

### 6.1 `<DeckCard />` (가장 중요한 컴포넌트)

```
┌────────────────────────────────────────────┐
│ [난이도 배지: easy/medium/hard]            │
│ 9코스트 정밀                                │
│                                            │
│ 추천 이유 (rationale, 2~3줄)               │
│ ────────────────────────────────────────── │
│ ▶ 핵심 기물    [야스오] [아리] [...]       │
│ ▶ 핵심 아이템  [무한의 대검] [...]         │
│ ▶ 추천 증강체  공격력/치명타 계열          │
│                                            │
│ 운영법                                     │
│  · 초반 (early): ...                       │
│  · 중반 (mid):   ...                       │
│  · 후반 (late):  ...                       │
│                                            │
│ ▶ 선택하기 좋은 조건                       │
│   · ...                                    │
│ ⚠ 피해야 하는 상황                         │
│   · ...                                    │
│ 🔄 안 풀릴 때 대체 플랜: ...               │
└────────────────────────────────────────────┘
```

| 요소 | 시각 처리 |
|---|---|
| 난이도 배지 | easy=green-500 / medium=amber-500 / hard=red-500 + 텍스트 (색만으로 구분 X) |
| 핵심 기물 칩 | hover 툴팁 (RAG 메타 — 코스트, 특성). MVP는 텍스트만, 시간 남으면 추가 |
| 카드 등장 | framer-motion `staggerChildren` 0.08s |

### 6.2 `<PatchBanner />`

```
┌─────────────────────────────────────────────┐
│ 📌 14.9 패치 기준 · 신뢰도: ●●○ (중간)      │
└─────────────────────────────────────────────┘
```

- `patch_version`: mount 시 `/api/patch-info`로 로드. 응답 받으면 응답값으로 갱신 (응답 patch가 우선).
- 신뢰도 도트: high=●●● green, medium=●●○ amber, low=●○○ red. 색 + 도트 동시.

### 6.3 `<SourcesPanel />`

각 source = 카드 1개. 제목 / URL / 발행일 / snippet. 외부 링크 아이콘. `target="_blank" rel="noopener noreferrer"` 필수.

기획서가 "출처 표시"를 핵심 가치로 강조하므로 **항상 펼친 상태**, 4개 이상이면 "더 보기".

### 6.4 `<WarningsPanel />`

`response.warnings` 배열을 노란 배경 박스로. 빈 배열이면 미렌더. 예:
- `"insufficient_data_after_patch"` → "패치 직후라 충분한 통계가 부족할 수 있어요"
- `"all_decks_filtered"` → "근거가 부족한 추천을 걸렀어요. 질문을 더 구체적으로 해보세요"
- `"research_truncated"` → "외부 정보 수집 시간이 초과돼 일부 정보가 빠졌을 수 있어요"

`warning_code → 사용자 메시지` 매핑은 `lib/warnings.ts`에 단일 정의.

---

## 7. 로딩 / 에러 UX

기획서가 "로딩/에러 UI"라고만 적어둠. Agent 응답이 평균 10~20초 걸리므로 progressive label 필수.

### 7.1 로딩 단계 (Frontend 측 타이머)

```
(0~3s)  사용자 조건 분석 중...
(3~8s)  최신 메타 정보 수집 중...
(8~15s) 추천 덱 구성 중...
(15~25s) 근거 정리 중...
```

- skeleton + 라벨 페이드인.
- Backend가 SSE 안 해도 충분 (MVP).
- 시간 남으면 SSE/스트리밍으로 진짜 단계 이벤트 (선택, `05-backend-spec.md` §3.1 확장).

### 7.2 에러 매핑 (Backend `error.code` ↔ UI)

| Backend code | UI |
|---|---|
| `validation_error` | 폼 인라인 에러 (필드 옆 빨간 메시지) |
| `intent_unsupported` | 결과 영역에 "이 질문은 아직 답할 수 없어요" + 예시 칩 강조 |
| `rate_limited` | 토스트 "잠시 후 다시 시도해주세요. (분당 5회 제한)" |
| `agent_timeout` | 결과 영역에 "응답이 너무 오래 걸려요" + 재시도 버튼 |
| `agent_failed` / `rag_unavailable` | 결과 영역에 "잠시 문제가 있어요" + request_id (작게) |
| 네트워크 실패 (fetch reject) | 동일 처리 |

`request_id`는 사용자에게 작게 노출 → 데모 중 디버깅 용이.

---

## 8. 상태 관리 (Zustand)

```ts
// src/lib/store.ts
import type { RecommendationResponse, Tier, PlayStyle } from "./schema";

type FormState = {
  tier: Tier | null;
  playStyle: PlayStyle | null;
  question: string;
  setTier(t: Tier): void;
  setPlayStyle(s: PlayStyle): void;
  setQuestion(q: string): void;
  reset(): void;
};

type ResultState = {
  status: "idle" | "loading" | "success" | "error";
  loadingStage: 0 | 1 | 2 | 3;          // 4단계 progressive label
  response: RecommendationResponse | null;
  error: { code: string; message: string; requestId?: string } | null;
  submit(): Promise<void>;
  reset(): void;
};

type PatchState = {
  patchVersion: string | null;
  lastUpdated: string | null;
  load(): Promise<void>;
};
```

3개 store 분리 (form / result / patch). 한 store에 몰지 않음.

---

## 9. API 클라이언트

```ts
// src/lib/api.ts
import { z } from "zod";
import { RecommendationResponseSchema } from "./schema";

const BASE = process.env.NEXT_PUBLIC_API_BASE!;

export class ApiError extends Error {
  constructor(public code: string, message: string, public requestId?: string) {
    super(message);
  }
}

export async function postRecommend(input: RecommendInput, signal?: AbortSignal) {
  const res = await fetch(`${BASE}/api/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(
      err?.error?.code ?? "unknown",
      err?.error?.message ?? "알 수 없는 오류",
      err?.error?.request_id,
    );
  }
  const json = await res.json();
  return RecommendationResponseSchema.parse(json); // 런타임 검증
}

export async function getPatchInfo() { /* ... */ }
export async function getExamples()  { /* ... */ }
export async function postFeedback(req: FeedbackRequest) { /* ... */ }
```

---

## 10. Zod schema 동기화

`07-data-contracts.md`의 JSON Schema를 Zod로 1:1 변환. **수동 동기**가 MVP 전략 (시간 남으면 `pydantic-to-zod` 자동화).

```ts
// src/lib/schema.ts (07-data-contracts §4와 1:1)
export const ConfidenceSchema = z.enum(["high", "medium", "low"]);
export const PhaseSchema = z.enum(["early", "mid", "late"]);

export const SourceSchema = z.object({
  title: z.string(),
  url: z.string().url(),
  published_at: z.string().nullable(),
  snippet: z.string().max(200),
});

export const PlaybookStepSchema = z.object({
  phase: PhaseSchema,
  instruction: z.string(),
});

export const DeckRecommendationSchema = z.object({
  name: z.string(),
  difficulty: z.enum(["easy", "medium", "hard"]),
  core_units: z.array(z.string()),
  key_items: z.array(z.string()),
  augment_direction: z.string(),
  playbook: z.array(PlaybookStepSchema).min(1),
  good_conditions: z.array(z.string()),
  avoid_conditions: z.array(z.string()),
  fallback_plan: z.string(),
  rationale: z.string().max(300),
});

export const RecommendationResponseSchema = z.object({
  request_id: z.string(),
  patch_version: z.string(),
  intent: z.string(),
  meta_summary: z.string(),
  decks: z.array(DeckRecommendationSchema).max(3),
  sources: z.array(SourceSchema),
  confidence: ConfidenceSchema,
  warnings: z.array(z.string()),
  generated_at: z.string(),
});

export type RecommendationResponse = z.infer<typeof RecommendationResponseSchema>;
```

PR 머지 룰: `07-data-contracts.md` 변경 시 `lib/schema.ts`도 같은 PR에 포함.

---

## 11. 환경변수

```
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false              # true면 tests/fixtures/mock_responses 사용
```

배포: `https://api.deckguru.example.com`.

---

## 12. 디자인 가이드

- **테마:** 다크 (롤토체스 분위기). Tailwind `slate`/`zinc` 계열 + 강조색 amber-400
- **글꼴:** Pretendard (본문), JetBrains Mono (덱 이름/기물 칩)
- **간격:** 8/16/24/32 grid
- **카드:** rounded-2xl, border, shadow-sm
- **모바일:** 360px 이상에서 카드 1열. 데스크톱 1024px+에서도 1열 (가로로 긴 카드는 가독성 ↓)

---

## 13. 디렉토리 구조

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Home
│   │   ├── about/page.tsx
│   │   └── demo/page.tsx
│   ├── components/
│   │   ├── RecommendForm/
│   │   │   ├── index.tsx
│   │   │   ├── TierSelect.tsx
│   │   │   ├── PlayStyleCards.tsx
│   │   │   ├── QuestionTextarea.tsx
│   │   │   └── ExampleChips.tsx
│   │   ├── ResultPanel/
│   │   │   ├── index.tsx
│   │   │   ├── DeckCard.tsx
│   │   │   ├── MetaSummaryCard.tsx
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   ├── SourcesPanel.tsx
│   │   │   └── WarningsPanel.tsx
│   │   ├── PatchBanner.tsx
│   │   ├── LoadingStages.tsx
│   │   ├── ErrorView.tsx
│   │   └── FeedbackBar.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── schema.ts                 # Zod (07-data-contracts와 1:1)
│   │   ├── store.ts                  # Zustand
│   │   ├── warnings.ts               # warning_code → 사용자 메시지
│   │   └── format.ts                 # 날짜, confidence 라벨 등
│   └── styles/globals.css
├── tailwind.config.ts
├── next.config.mjs
└── package.json
```

---

## 14. 테스트

| 종류 | 도구 | 대상 |
|---|---|---|
| Component | Vitest + React Testing Library | DeckCard, ResultPanel, RecommendForm 렌더링 |
| Schema | Vitest | Zod round-trip with mock fixture |
| E2E (선택) | Playwright | 4개 example chip 시나리오 |

`05-backend-spec.md` §8의 mock fixture를 import해서 컴포넌트 테스트 → Backend 미완성 시에도 UI 완성 가능.

---

## 15. 접근성 / 반응형

- 모든 인터랙티브 요소 키보드 포커스 가능 (`focus-visible:ring-2`)
- 색만으로 상태 구분 X (난이도 / 신뢰도 모두 색 + 텍스트/도트)
- 텍스트 ↔ 배경 명도 대비 4.5 이상
- `aria-live="polite"`로 결과 등장 시 스크린리더 알림
- 360px 가로에서 잘림 없음

---

## 16. 데모 시나리오 (5/9 발표용)

`/demo` 페이지에서 3개 골든 시나리오 (`evals/golden_set.jsonl`과 일치) 빠른 호출 버튼.

| # | tier | style | question |
|---|---|---|---|
| 1 | GOLD | stable_top4 | 현재 패치에서 골드가 티어 올리기 좋은 덱 3개 추천해줘 |
| 2 | PLATINUM | high_risk_first | 요즘 많이 나오는 덱 하나 골라서 초반부터 후반까지 운영법 알려줘 |
| 3 | SILVER | easy_beginner | 초반에 곡궁이 많이 나왔는데 어떤 덱 가면 좋아? |

3개 모두 캐시 워밍 (`05-backend-spec.md` §4.1 L2 SQLite). 발표 중 응답 ≤ 1s. 라이브 시연 시 새 질문 1개 시도 + 백업 시나리오.

---

## 17. 기획서 피드백

| # | 기획서 | 문제 | 본 spec |
|---|---|---|---|
| 1 | "Axios 또는 Fetch", "Zustand 또는 Context"(§4.1.1) | 결정 안 함 = 코드 스타일 갈림 | §2 fetch + Zustand로 못박음 |
| 2 | "결과 카드, 화면 전환 애니메이션"(§4.1.1) | 카드 1개 구성이 미정 | §6 컴포넌트 트리 + ASCII 레이아웃 |
| 3 | 로딩 UI(§5.3.5) | "로딩"만 적힘. 10~20s 침묵하면 사용자 떠남 | §7.1 4단계 progressive label |
| 4 | 에러 처리(§4.3) | 사용자 메시지만 있고 code↔UI 매핑 X | §7.2 매핑 표 |
| 5 | 출처 표시(§1.6 핵심 가치) | UI 비중 미정 | §6.3 항상 펼침 |
| 6 | 신뢰도 표시 | "높음/중간/낮음" 텍스트만 | §6.2 색 + 도트 |
| 7 | 패치 기준 표시 위치 | 응답에 patch_version 있는데 UI 비중 미정 | §6.2 항상 상단 노출 |
| 8 | 후속 질문(§3.2.1 9번) | 멀티턴이 데모에 들어갈지 불명 | MVP 미지원 (단발). v2 백로그 |
| 9 | 모바일 / 접근성 | 미언급 | §12, §15 최소 기준 |
| 10 | 예시 질문 노출 | 표지 4개 시나리오만 적힘 | §5.2 example chip |
| 11 | 페이지 수 | "결과 화면" 한 줄(§5.3.5) | §3 single page unfold |
| 12 | 스트리밍 | 미언급 | §7.1 노트로 향후 SSE 확장 |
