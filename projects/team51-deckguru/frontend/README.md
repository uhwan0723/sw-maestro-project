# DeckGuru Frontend (51조)

`frontend/`는 DeckGuru의 Next.js 프론트엔드입니다. 사용자는 메인 화면에서 티어, 플레이 스타일, 질문을 입력하고 추천 결과 화면에서 덱, 운영 단계, 근거, 경고, 디버그 정보를 확인합니다.

현재 프론트엔드는 백엔드 API와 목 데이터를 모두 지원합니다. 로컬에서 백엔드 없이 화면 흐름을 확인하려면 `NEXT_PUBLIC_USE_MOCK=true`를 사용하세요.

## 기술 스택

| 항목            | 버전 / 도구                                         | 설명                                           |
| --------------- | --------------------------------------------------- | ---------------------------------------------- |
| Framework       | `Next.js 16.1.7`                                    | App Router 기반 애플리케이션                   |
| UI Runtime      | `React 19.2.4`                                      | Client Component, form state, provider 구성    |
| Language        | `TypeScript 5.9.3`                                  | `strict` 모드와 `@/*` 경로 alias 사용          |
| Styling         | `Tailwind CSS 4.2.1`                                | `src/app/globals.css` 중심 전역 스타일         |
| Data Fetching   | `@tanstack/react-query 5.100.9`                     | 추천 요청 mutation, 결과 캐시, 패치 정보 query |
| Validation      | `zod 4.4.3`                                         | API 요청과 응답 스키마 검증                    |
| UI Library      | `@base-ui/react`, `shadcn`, `@phosphor-icons/react` | 공통 UI와 아이콘                               |
| Theme           | `next-themes`                                       | 라이트/다크 테마 provider                      |
| Package Manager | `pnpm 10.28.2`                                      | `frontend/pnpm-lock.yaml` 기준                 |

## 빠른 실행

```bash
cd frontend
pnpm install
pnpm dev
```

개발 서버 기본 주소는 `http://localhost:3000`입니다.

백엔드와 연결해서 실행하려면 백엔드를 `http://localhost:8000`에서 먼저 실행하고, `frontend/.env.local`에 다음 값을 둡니다.

```bash
NEXT_PUBLIC_USE_MOCK=false
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=
```

이 설정에서는 브라우저가 같은 origin의 `/api/*`로 요청하고, `next.config.mjs`의 rewrite가 백엔드 `/api/*`로 전달합니다.

백엔드 없이 목 데이터로 실행하려면 `frontend/.env.local`에서 다음 값을 사용하세요.

```bash
NEXT_PUBLIC_USE_MOCK=true
```

## 디렉토리 구조

생성물인 `.next/`와 `node_modules/`는 제외했습니다.

```text
frontend/
├── package.json              # 개발, 빌드, 검사 스크립트
├── pnpm-lock.yaml            # pnpm lockfile
├── next.config.mjs           # Next.js 설정, React Compiler 활성화
├── tsconfig.json             # TypeScript 설정, @/* alias
├── eslint.config.mjs         # ESLint 설정
├── prettier.config.mjs       # Prettier와 Tailwind 정렬 설정
├── postcss.config.mjs        # Tailwind CSS 4 PostCSS 설정
├── components.json           # shadcn UI 설정
├── public/                   # 웹 앱 manifest 이미지
└── src/
    ├── api/                  # API endpoint, query, mutation, 타입
    │   ├── api-url.ts
    │   ├── get-patch-info/
    │   └── post-recommend/
    ├── app/                  # Next.js App Router
    │   ├── layout.tsx        # 전역 provider, 폰트, metadata
    │   ├── globals.css       # Tailwind 전역 스타일과 디자인 토큰
    │   ├── manifest.json
    │   ├── (main)/           # 메인 추천 입력 화면
    │   └── recommendations/
    │       └── [requestId]/  # 추천 결과 화면
    ├── assets/fonts/         # Galmuri 로컬 폰트
    ├── components/
    │   ├── providers/        # Theme, Query, Motion provider
    │   └── ui/               # Button, Input, Select, Badge
    ├── constants/            # 환경 플래그와 앱 경로
    ├── hooks/                # 공통 hook 확장 위치
    ├── lib/                  # API client, schema, query client, 유틸
    ├── mocks/                # 추천 응답과 패치 정보 목 데이터
    └── types/                # 전역 타입 선언
```

## 주요 화면 흐름

메인 화면은 `src/app/(main)/page.tsx`에서 시작합니다. 실제 입력 폼 로직은 `src/app/(main)/_hooks/use-deck-recommendation-form.ts`가 담당합니다.

1. 사용자가 질문, 티어, 플레이 스타일을 입력합니다.
2. `usePostRecommendMutation`이 `postRecommend`를 호출합니다.
3. 성공 응답은 `recommendationResultQueryKey(request_id)`로 React Query 캐시에 저장됩니다.
4. 라우터가 `/recommendations/{requestId}`로 이동합니다.
5. 결과 화면은 캐시에 저장된 추천 결과를 읽어 렌더링합니다.

주의할 점은 추천 결과 화면이 현재 캐시 기반이라는 점입니다. 결과 페이지 URL을 새로고침하거나 직접 열면 캐시가 비어 있으므로 `EmptyResultState`가 표시됩니다.

## API 구조

API 경로 상수는 `src/api/api-url.ts`에 있습니다.

| 기능                | 프론트엔드 endpoint      | 구현 위치                 |
| ------------------- | ------------------------ | ------------------------- |
| 덱 추천 요청        | `/api/recommend`         | `src/api/post-recommend/` |
| 패치 정보 조회      | `/api/patch-info`        | `src/api/get-patch-info/` |
| 예시 질문 조회 예정 | `/api/example-questions` | 상수만 정의됨             |
| 피드백 전송 예정    | `/api/feedback`          | 상수만 정의됨             |

공통 요청 함수는 `src/lib/api-client.ts`에 있습니다. 요청 timeout은 30초입니다. 서버에서는 `API_BASE_URL`을 우선 사용하고, 없으면 `NEXT_PUBLIC_API_BASE_URL`을 사용합니다. 브라우저에서는 `NEXT_PUBLIC_API_BASE_URL`만 사용합니다.
`NEXT_PUBLIC_API_BASE_URL`이 비어 있으면 같은 origin의 `/api/*`로 요청하며, `next.config.mjs`가 `API_BASE_URL` 또는 기본값 `http://localhost:8000`으로 프록시합니다.

API 요청과 응답은 `src/lib/schema.ts`의 Zod 스키마로 검증합니다. 백엔드 응답 필드가 스키마와 다르면 프론트엔드에서 파싱 오류가 납니다.

## 환경변수

| 변수                       | 기본값                  | 사용 위치                                  | 설명                                                                                                                        |
| -------------------------- | ----------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_USE_MOCK`     | `false`                 | `src/constants/env.ts`                     | `true`이면 추천 요청과 패치 정보 조회가 `src/mocks/` 데이터를 반환합니다.                                                   |
| `NEXT_PUBLIC_API_BASE_URL` | 빈 문자열               | `src/lib/api-client.ts`                    | 브라우저에서 직접 호출할 공개 API base URL입니다. 값이 없으면 같은 origin의 `/api/*`로 요청합니다.                          |
| `API_BASE_URL`             | `http://localhost:8000` | `next.config.mjs`, `src/lib/api-client.ts` | Next.js rewrite와 서버 요청에서 사용하는 백엔드 API base URL입니다. 서버 실행 시 `NEXT_PUBLIC_API_BASE_URL`보다 우선합니다. |
| `NEXT_PUBLIC_BASE_URL`     | `http://localhost:3000` | `src/constants/app-path.ts`                | 앱 base URL이 필요할 때 사용하는 공개 URL입니다.                                                                            |

예시:

```bash
# frontend/.env.local
NEXT_PUBLIC_USE_MOCK=false
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=
```

브라우저에서 백엔드를 직접 호출하고 싶다면 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`으로 설정할 수 있습니다. 이 경우 백엔드 CORS 허용 origin에 현재 프론트엔드 주소가 포함되어 있어야 합니다.

## 목 데이터 사용 방법

목 데이터는 `src/mocks/`에 있습니다.

| 파일                          | 용도                   |
| ----------------------------- | ---------------------- |
| `src/mocks/recommendation.ts` | 추천 결과 목 응답 3종  |
| `src/mocks/patch-info.ts`     | 현재 패치 정보 목 응답 |

`NEXT_PUBLIC_USE_MOCK=true`이면 `postRecommend`와 `getPatchInfo`가 실제 API를 호출하지 않습니다.

추천 응답은 질문 문자열에 따라 선택됩니다.

| 질문 조건                  | 반환 데이터                 |
| -------------------------- | --------------------------- |
| `운영법` 포함              | `mockDeckPlaystyleResponse` |
| `곡궁` 포함 또는 `BF` 포함 | `mockItemPivotResponse`     |
| 그 외                      | `mockRecommendDeckResponse` |

목 데이터도 `src/lib/schema.ts`의 스키마를 통과해야 합니다. 목 응답을 수정할 때는 `patch_version`, `intent`, `decks`, `sources`, `generated_at` 같은 필수 필드를 유지하세요.

## 스크립트

```bash
pnpm dev        # 개발 서버 실행
pnpm build      # 프로덕션 빌드
pnpm start      # 빌드 결과 실행
pnpm lint       # ESLint 검사
pnpm typecheck  # TypeScript 타입 검사
pnpm format     # Prettier 포맷
```

## 개발 규칙

- import 경로는 `@/*` alias를 사용합니다.
- API 계약은 `src/lib/schema.ts`에 먼저 반영한 뒤 API 타입에서 재사용합니다.
- React Query 설정은 `src/lib/query-client.ts`에서 관리합니다.
- 전역 provider는 `src/app/layout.tsx`에 추가합니다.
- 공통 UI는 `src/components/ui/`에 두고, 화면 전용 컴포넌트는 해당 route의 `_components/`에 둡니다.
- 화면 전용 hook은 해당 route의 `_hooks/`에 둡니다.

## 검증

변경 후 다음 명령을 실행하세요.

```bash
pnpm lint
pnpm typecheck
pnpm build
```

목 데이터 흐름까지 확인하려면 `NEXT_PUBLIC_USE_MOCK=true`로 개발 서버를 실행한 뒤 다음 순서로 확인합니다.

1. `http://localhost:3000`에 접속합니다.
2. 티어와 플레이 스타일을 선택합니다.
3. 질문을 직접 입력하거나 예시 질문 칩을 선택합니다.
4. 추천 버튼을 눌러 `/recommendations/{requestId}` 결과 화면으로 이동하는지 확인합니다.
