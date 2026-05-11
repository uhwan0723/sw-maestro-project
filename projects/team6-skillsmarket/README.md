# Skills Market

## 프로젝트 소개
Skills Market은 다양한 기술 스택과 관련된 정보를 제공하고 관리하는 마켓플레이스 서비스입니다. 
본 프로젝트는 프론트엔드와 백엔드가 분리된 구조로, 빌드 도구 없이 구현된 Vanilla JS 기반의 SPA(Single Page Application)와 Spring Boot 기반의 강력한 REST API 서버로 구성되어 있습니다. 특히 향후 Spring AI를 활용한 OpenAI 임베딩 기반의 벡터 검색 확장을 고려하여 설계되었습니다.

## 프로젝트 구조
- `frontend/`: Vanilla JS 기반의 순수 ESM SPA (프론트엔드)
- `backend/`: Java, Spring Boot 기반의 REST API (백엔드)

## 주요 기능
- **스킬 기본 조회**: 카테고리별 스킬 목록 및 마크다운 기반의 상세 정보 조회
- **AI 기반 스킬 생성**: 사용자 프롬프트에 따른 스킬 데이터 비동기 생성 및 SSE를 통한 실시간 상태 모니터링
- **스킬 벡터 검색 및 추천**: Spring AI를 활용한 전체 스킬 벡터 임베딩 및 자연어 쿼리 기반 유사 스킬 추천

## 기술 스택

### Frontend
- **Core**: HTML5, CSS3, JavaScript (Vanilla JS, ES Modules)
- **Architecture**: No-build-tool SPA, 보안(XSS 방지) 및 모달 접근성 중점 설계
- **Testing**: Node.js Native Test Runner (`node:test`)

### Backend
- **Language**: Java 21
- **Framework**: Spring Boot 4.0.6
- **Database**: H2 Database (In-memory, 테스트 및 로컬 환경용), MySQL (운영 환경용)
- **ORM**: Spring Data JPA, Hibernate
- **AI**: Spring AI (OpenAI, Vector Store)
- **API Docs**: Swagger (springdoc-openapi 3.0.3)
- **Build Tool**: Gradle

---

## 실행 방법

### Backend 실행
백엔드 프로젝트를 먼저 실행하여 프론트엔드에서 호출할 API 서버를 띄워야 합니다.

1. `backend` 디렉토리로 이동합니다.
```bash
cd backend
```
2. OpenAI API 키를 환경 변수로 설정합니다.
```bash
export OPENAI_API_KEY="your-openai-api-key"
```
3. 애플리케이션을 실행합니다.
```bash
# macOS / Linux
./gradlew bootRun

# Windows
gradlew.bat bootRun
```
* **Swagger API 문서**: [http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)
* **H2 DB 콘솔**: [http://localhost:8080/h2-console](http://localhost:8080/h2-console) (JDBC URL: `jdbc:h2:mem:skillsmarket`, User Name: `sa`)

### Frontend 실행
Frontend는 별도의 빌드 과정이 없으므로 정적 파일 서버를 통해 쉽게 실행할 수 있습니다.

1. `frontend` 디렉토리로 이동합니다.
```bash
cd frontend
```
2. 선호하는 로컬 웹 서버를 실행합니다. (VS Code의 Live Server 확장을 사용하셔도 됩니다.)
```bash
# Python 3가 설치된 경우
python3 -m http.server 3000

# Node.js npx를 사용하는 경우
npx serve .
```
3. 웹 브라우저에서 `http://localhost:3000` (또는 실행된 포트)로 접속합니다.

### Frontend 테스트
```bash
cd frontend
npm test
```
