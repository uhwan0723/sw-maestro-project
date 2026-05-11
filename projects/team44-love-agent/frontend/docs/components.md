# 컴포넌트 목록

UI 이미지 기준으로 구성한 컴포넌트 목록입니다.
각 컴포넌트는 하나의 역할만 담당하도록 분리했습니다.

---

## 폴더 구분 기준

`components/` 안의 폴더는 **"이 컴포넌트가 무엇에 관한 것인가"** 기준으로 나눴습니다.

| 폴더 | 기준 | 담고 있는 것 |
| --- | --- | --- |
| `ui/` | shadcn이 생성하는 기본 단위 | Button, Card, Badge 등 — 직접 수정 거의 없음 |
| `layout/` | 화면의 뼈대와 틀 | 사이드바, 스텝바, 우측 패널 — 어느 화면에서나 공통으로 보이는 구조 |
| `agents/` | 에이전트 자체를 표현 | 아바타, 배지, 카드 — "누가 말하는가"와 관련된 것 |
| `consultation/` | 상담 흐름의 각 단계 콘텐츠 | 입력폼, 의견 그리드, 토론, 결과 — "무슨 내용을 보여주는가"와 관련된 것 |
| `status/` | 데이터 없거나 처리 중인 상태 | 로딩, 에러, 빈 화면 — 정상 콘텐츠 대신 보여주는 것 |
| `common/` | 위 어디에도 속하지 않는 범용 조각 | 섹션 제목, 구분선, 라운드 태그 — 여러 폴더에서 공통으로 사용 |

> `agents/`와 `consultation/`의 차이:
> - `agents/` — 에이전트 프로필, 이름, 배지처럼 **에이전트 자체**를 나타내는 것
> - `consultation/` — 에이전트가 참여하는 **상담 단계의 콘텐츠**를 나타내는 것
> - 예: `AgentAvatar`는 agents/, `DiscussionMessage`(발언 내용)는 consultation/

---

## shadcn/ui 기본 컴포넌트 (`components/ui/`)

`npx shadcn@latest add` 명령으로 설치하는 컴포넌트들입니다.
커스텀 컴포넌트들은 여기서 import해서 조합합니다.

| 컴포넌트 | 설치 명령 | 사용처 |
| --- | --- | --- |
| `button.tsx` | `add button` | 상담 시작, 다음 단계, 재시도 버튼 |
| `card.tsx` | `add card` | 에이전트 의견 카드, 결과 카드 |
| `avatar.tsx` | `add avatar` | 에이전트 프로필 이미지 |
| `badge.tsx` | `add badge` | 에이전트 태그, 스탠스 표시, 라운드 태그 |
| `textarea.tsx` | `add textarea` | 고민 입력창 |
| `skeleton.tsx` | `add skeleton` | 로딩 상태 |
| `scroll-area.tsx` | `add scroll-area` | 사이드바, 토론 로그 스크롤 |
| `separator.tsx` | `add separator` | 섹션 구분선 |

> 한 번에 설치: `npx shadcn@latest add button card avatar badge textarea skeleton scroll-area separator`

---

## 레이아웃 (`components/layout/`)

| 컴포넌트 | 역할 | shadcn 사용 |
| --- | --- | --- |
| `RootLayout` | 사이드바 + 메인 영역 전체 레이아웃 | - |
| `Sidebar` | 좌측 에이전트 목록 패널 | `ScrollArea` |
| `StepBar` | 상단 진행 단계 표시 (고민 입력 → 의견 분석 → 1라운드 → 2라운드 → 최종 결과, 총 5단계) | `Badge` |
| `RightPanel` | 우측 패널 껍데기 — 현재 단계에 따라 `RoundSummaryPanel` 또는 `FinalProgressPanel`을 렌더링 | `Card` |
| `RoundSummaryPanel` | 토론 단계 우측 패널 — 찬/반/중립 체크리스트 + 다음 단계 이동 버튼 | `Card`, `Button` |
| `FinalProgressPanel` | 최종 결과 화면 우측 패널 — 전체 진행률 체크리스트 | `Card` |

---

## 에이전트 (`components/agents/`)

| 컴포넌트 | 역할 | shadcn 사용 |
| --- | --- | --- |
| `AgentAvatar` | 에이전트 프로필 이미지 + 이름 | `Avatar` |
| `AgentBadge` | 에이전트 페르소나 태그 (현실주의자 등) | `Badge` |
| `AgentCard` | 에이전트 의견 카드 (이름 + 의견 + 근거) — **정적 카드 형태**, 의견 분석 단계에서 6개 그리드로 표시 | `Card` |
| `AgentSidebarItem` | 사이드바에서 에이전트 한 줄 표시 | `Avatar`, `Badge` |
| `StanceIndicator` | 찬성 / 반대 / 보완 스탠스 표시 | `Badge` |

---

## 상담 흐름 (`components/consultation/`)

| 컴포넌트 | 역할 | shadcn 사용 |
| --- | --- | --- |
| `UserInputBanner` | 입력한 고민 텍스트 미리보기 바 — 상담 진행 화면 상단에 고정 표시 | `Card` |
| `HowItWorks` | 입력 화면 하단 상담 방식 안내 (아이콘 + 설명 3~4개) | - |
| `InputForm` | 고민 입력창 + 상담 시작 버튼 | `Textarea`, `Button` |
| `OpinionGrid` | 의견 분석 단계 — 에이전트 6개 초기 의견 그리드 | `Card` |
| `OpinionPhase` | 의견 분석 단계 전체를 감싸는 중간 레이어 — `UserInputBanner` + `OpinionGrid` 조합 | - |
| `DiscussionPhase` | 토론 단계 전체를 감싸는 중간 레이어 — `UserInputBanner` + `DiscussionRound` 조합 | - |
| `ResultPhase` | 최종 결과 단계 전체를 감싸는 중간 레이어 — `FinalResult` + `FinalAgentSummary` 조합 | - |
| `DiscussionRound` | 특정 라운드의 토론 내용 전체 — `RoundTag` + `DiscussionMessage` 목록 | - |
| `DiscussionMessage` | 토론 내 에이전트 발언 — **말풍선 형태**, 다른 에이전트 발언을 인용하는 경우 인용 블록 포함. `AgentCard`(정적 카드)와 달리 채팅처럼 순서대로 쌓임 | `Avatar` |
| `RoundSummary` | 라운드별 에이전트 찬/반/중립 스탠스 체크리스트 (RightPanel 내부에서 사용) | `Separator` |
| `ResultCategoryCard` | 최종 결과 카테고리 카드 한 개 (사랑 방식, 소통 방법 등 항목별) | `Card`, `Badge` |
| `FinalResult` | 최종 결과 전체 — `ResultCategoryCard` 그리드 + 상황 요약 + 최종 조언 | `Card` |
| `FinalAgentSummary` | 최종 결과 하단 에이전트 프로필 재표시 + 저장 버튼 | `Avatar`, `Button` |

---

## 상태 표시 (`components/status/`)

| 컴포넌트 | 역할 | shadcn 사용 |
| --- | --- | --- |
| `LoadingCard` | 에이전트 의견 생성 중 로딩 카드 | `Skeleton`, `Card` |
| `LoadingOverlay` | 전체 로딩 오버레이 (상담 시작 시) | `Skeleton` |
| `ErrorMessage` | 에러 발생 시 메시지 + 재시도 버튼 | `Button` |
| `EmptyState` | 데이터 없을 때 빈 화면 안내 | - |

---

## 공통 (`components/common/`)

| 컴포넌트 | 역할 | shadcn 사용 |
| --- | --- | --- |
| `SectionTitle` | 섹션 제목 + 부제목 텍스트 | - |
| `Divider` | 섹션 구분선 | `Separator` |
| `RoundTag` | "1라운드", "2라운드" 등 라운드 구분 태그 | `Badge` |

---

## 페이지 구성 (`app/`)

| 파일 | 화면 | 사용 컴포넌트 |
| --- | --- | --- |
| `app/page.tsx` | 고민 입력 화면 | `InputForm`, `HowItWorks`, `Sidebar` |
| `app/consultation/[sessionId]/page.tsx` | 상담 진행 + 결과 화면 — Zustand 단계 상태에 따라 `OpinionPhase` / `DiscussionPhase` / `ResultPhase` 중 하나를 렌더링 | `StepBar`, `Sidebar`, `RightPanel`, `OpinionPhase`, `DiscussionPhase`, `ResultPhase` |

---

## 컴포넌트 개발 순서 (권장)

API 명세 없이도 목업 데이터로 개발 가능한 순서입니다.

1. **디자인 토큰** — 색상, 타이포 세팅 (`tailwind.config.ts`)
2. **공통 컴포넌트** — `AgentAvatar`, `AgentBadge`, `RoundTag`
3. **레이아웃** — `Sidebar`, `StepBar`, `RootLayout`
4. **입력 화면** — `InputForm`, `HowItWorks`
5. **의견 단계** — `AgentCard`, `OpinionGrid`, `UserInputBanner` → `OpinionPhase`로 조합
6. **토론 단계** — `DiscussionMessage`, `DiscussionRound` → `DiscussionPhase`로 조합
7. **결과 단계** — `ResultCategoryCard`, `FinalResult`, `FinalAgentSummary` → `ResultPhase`로 조합
8. **우측 패널** — `RoundSummaryPanel`, `FinalProgressPanel` → `RightPanel`에 연결
9. **상태 컴포넌트** — `LoadingCard`, `ErrorMessage`
10. **API 연결** — `services/` 작성 후 목업 데이터 교체
