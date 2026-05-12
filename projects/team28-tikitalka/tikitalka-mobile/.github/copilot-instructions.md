# GitHub Copilot Instructions

## 언어
- PR 리뷰, 코드 리뷰, 코멘트, 제안 등 **모든 응답은 한국어**로 작성한다.

## 프로젝트 개요
- 해외 축구 이슈 요약 및 AI 챗봇 서비스의 모바일 클라이언트다.
- **KMP (Kotlin Multiplatform) + CMP (Compose Multiplatform)** 기반으로 Android / iOS를 동시 지원한다.
- **Clean Architecture + MVI** 패턴을 적용하며, DI는 Koin, 네트워크는 Ktor Client를 사용한다.

## 모듈 구조 & 의존성 방향

```
composeApp (UI)
    └─ shared
        ├─ domain   (순수 Kotlin — 외부 의존 없음)
        ├─ data     (domain 인터페이스 구현)
        ├─ presentation (ViewModel / MVI)
        └─ di       (Koin 모듈)
```

- `domain`이 `data` / `presentation` / 외부 라이브러리를 참조하는 역방향 의존성은 허용하지 않는다.
- `presentation`은 `domain`의 UseCase만 참조한다. `data` 구현체를 직접 참조하지 않는다.
- `data`는 `domain` 인터페이스를 구현한다 (DIP).
- 의존성 연결은 `di` 패키지의 Koin 모듈에서만 수행한다.

## 코딩 컨벤션
- **Kotlin 전용** — Java 파일 추가 금지.
- **Jetpack Compose 전용** — XML 레이아웃 금지.
- `commonMain`에 최대한 코드를 집중하고, 플랫폼별(`androidMain` / `iosMain`) 코드는 최소화한다.
- 파일 하나에 클래스/인터페이스 하나.
- 패키지 네이밍: `com.soma2026.tikitalka.<layer>.<feature>`.

## 아키텍처 규칙

### Domain 레이어
- 순수 Kotlin만 사용한다. Android 프레임워크, Ktor, Koin 등 외부 라이브러리 의존 금지.
- `Repository`는 인터페이스만 정의한다. 구현체는 `data` 레이어에 위치한다.
- `UseCase`는 단일 책임 — `suspend operator fun invoke()` 하나만 갖는다.
- 도메인 모델은 불변 `data class`로 정의한다.

### Data 레이어
- `RepositoryImpl`은 반드시 `domain`의 Repository 인터페이스를 구현한다.
- DTO와 도메인 모델은 반드시 분리한다.
- DTO → 도메인 변환은 DTO 파일 내 확장함수(`fun XxxDto.toDomain()`)로 구현한다. 별도 Mapper 파일을 만들지 않는다. (DTO 변경과 변환 로직 변경이 항상 함께 발생하므로 같은 파일에 공존시킨다)
- DTO에는 `@Serializable`을 붙인다.
- API 호출 결과는 반드시 `runCatching`으로 감싸 `Result<T>`를 반환한다.

### Presentation 레이어 (MVI)
- `ViewModel`은 UseCase만 참조한다. Repository 직접 참조 금지.
- `State`는 불변 `data class`이며, `_state.update { it.copy(...) }`로만 갱신한다.
- 네비게이션, 토스트 등 일회성 이벤트는 `Effect`(Channel)로 처리한다. `State`로 처리하지 않는다.
- `viewModelScope.launch` 안에서 코루틴을 실행한다.

### DI (Koin)
- 인터페이스 ↔ 구현체 바인딩은 Koin 모듈(`di` 패키지)에서만 수행한다.
- `single<Interface> { Impl(get()) }` 형식으로 DIP를 실현한다.

## PR 리뷰 시 중점 확인 항목
1. 의존성 방향이 위 규칙을 위반하지 않는지 확인한다. (특히 `domain`의 역방향 의존 여부)
2. `domain`에 Android / Ktor / Koin 등 외부 라이브러리 의존성이 유입되지 않았는지 확인한다.
3. DTO → 도메인 변환이 DTO 파일 내 `toDomain()` 확장함수로 구현되었는지 확인한다. (별도 Mapper 파일 금지)
4. `ViewModel`이 UseCase만 참조하고 Repository를 직접 참조하지 않는지 확인한다.
5. 일회성 이벤트(네비게이션, 토스트)를 `State` 대신 `Effect`로 처리했는지 확인한다.
6. `State`가 불변 `data class`이고 `copy()`로만 갱신되는지 확인한다.
7. API 호출 결과가 `runCatching`으로 감싸져 `Result<T>`를 반환하는지 확인한다.
8. `commonMain`에 작성 가능한 코드가 플랫폼별 소스셋에 분산되지 않았는지 확인한다.
