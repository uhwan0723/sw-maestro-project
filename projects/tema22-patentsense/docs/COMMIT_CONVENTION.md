# Commit Convention

## 1. 커밋 메시지 형식

커밋 메시지는 Conventional Commits 형식을 사용한다.

```txt
<type>: <summary>
```

예시:

```txt
feat: KIPRIS 특허 검색 도구 추가
fix: 유사도 점수 정규화 오류 수정
docs: AI 에이전트 팀 컨벤션 추가
refactor: 특허 분석 그래프 노드 분리
test: 키워드 추출 프롬프트 테스트 추가
chore: FastAPI 개발 환경 설정
```

## 2. type 규칙

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 작성 또는 수정
- `refactor`: 동작 변경 없는 코드 구조 개선
- `test`: 테스트 추가 또는 수정
- `chore`: 설정, 의존성, 빌드, 기타 작업

## 3. summary 규칙

- summary는 50자 이내를 권장한다.
- 마침표를 붙이지 않는다.
- 무엇을 바꿨는지 명확히 쓴다.
- 한 커밋에는 하나의 논리적 변경만 포함한다.

좋은 예:

```txt
feat: LangGraph 특허 분석 플로우 추가
fix: KIPRIS 빈 응답 처리 오류 수정
docs: MVP 범위 문서 정리
```

나쁜 예:

```txt
fix: 수정
feat: 이것저것 추가
update: 코드 변경
```

## 4. 브랜치 이름

브랜치 이름은 아래 형식을 따른다.

```txt
<type>/<short-description>
```

예시:

```txt
feat/kipris-search-tool
feat/langgraph-patent-flow
fix/patent-score-normalization
docs/ai-agent-convention
```

## 5. AI 생성 코드 커밋 규칙

- AI가 만든 코드는 사람이 읽고 검토한 뒤 커밋한다.
- AI가 제안한 변경이라도 프로젝트 구조와 MVP 범위에 맞지 않으면 수정한다.
- API Key, 토큰, 비밀번호, 개인정보가 포함되지 않았는지 확인한다.
- 특허 분석 결과를 법적 판단처럼 표현하는 문구가 없는지 확인한다.
- 민감 정보가 커밋된 경우 즉시 팀에 공유하고 해당 키를 폐기한다.
