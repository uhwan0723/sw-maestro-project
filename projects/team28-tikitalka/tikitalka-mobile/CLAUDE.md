# 티키타카 (TikiTalka) - Mobile

## 프로젝트 개요
해외 축구 이슈 요약 및 AI 챗봇 서비스의 모바일 클라이언트.
화제성 높은 축구 뉴스를 큐레이션하고, AI와 실시간 티키타카(대화)를 제공하는 앱.

## 디자인 참고
- UI 디자인: `docs/TikiTalka.html` 참고
- 피드 화면: 뉴스 카드 리스트만 구현 (기타 컴포넌트 생략)
- 채팅 화면: 메시지 버블 UI 참고

## 기술 스택
- **언어**: Kotlin
- **멀티플랫폼**: KMP (Kotlin Multiplatform) + CMP (Compose Multiplatform)
- **타겟 플랫폼**: Android, iOS
- **아키텍처**: Clean Architecture + MVI
- **DI**: Koin (KMP 지원)
- **네트워크**: Ktor Client
- **빌드**: Gradle (Kotlin DSL)
- **최소 SDK**: Android API 28 (Android 9.0)

---

## 아키텍처 원칙

### 의존성 방향 (DIP 적용)

```
UI (CMP) → Presentation → Domain ← Data
                             ↑
                     인터페이스 정의
                     구현체는 Data가 담당
```

- **Domain은 아무것도 의존하지 않는다** (순수 Kotlin, 외부 라이브러리 최소화)
- **Data가 Domain을 바라본다** (Domain 인터페이스를 Data에서 구현)
- **Presentation은 Domain UseCase만 안다** (Data 구현체를 직접 참조하지 않는다)
- **의존성 주입은 Koin이 담당** (구현체 연결은 DI 모듈에서만)

### 레이어별 역할

| 레이어 | 위치 | 역할 |
|--------|------|------|
| UI | `composeApp` | Composable 화면, 사용자 이벤트 전달 |
| Presentation | `shared/presentation` | State/Intent/Effect 관리, UseCase 호출 |
| Domain | `shared/domain` | UseCase, 비즈니스 규칙, Repository **인터페이스** 정의 |
| Data | `shared/data` | Repository **구현체**, Ktor API, DTO ↔ Model 변환 |

---

## 프로젝트 구조

```
tikitalka-mobile/
├── composeApp/
│   └── src/
│       ├── commonMain/
│       │   └── kotlin/com/tikitalka/
│       │       ├── App.kt
│       │       ├── navigation/
│       │       └── ui/
│       │           ├── dashboard/
│       │           │   └── DashboardScreen.kt
│       │           └── chat/
│       │               └── ChatScreen.kt
│       ├── androidMain/
│       └── iosMain/
│
├── shared/
│   └── src/
│       └── commonMain/
│           └── kotlin/com/tikitalka/
│               │
│               ├── domain/                         # 순수 비즈니스 로직 (외부 의존 없음)
│               │   ├── model/
│               │   │   ├── Issue.kt
│               │   │   └── ChatMessage.kt
│               │   ├── repository/                 # 인터페이스만 정의
│               │   │   ├── IssueRepository.kt      # ← Data가 구현
│               │   │   └── ChatRepository.kt       # ← Data가 구현
│               │   └── usecase/
│               │       ├── GetIssuesUseCase.kt
│               │       ├── GetIssueDetailUseCase.kt
│               │       ├── SendChatMessageUseCase.kt
│               │       └── GetChatHistoryUseCase.kt
│               │
│               ├── data/                           # 인프라 구현 (Domain 인터페이스 구현)
│               │   ├── remote/
│               │   │   ├── api/
│               │   │   │   ├── IssueApi.kt
│               │   │   │   └── ChatApi.kt
│               │   │   └── dto/
│               │   │       ├── IssueDto.kt
│               │   │       └── ChatMessageDto.kt
│               │   ├── mapper/                     # DTO → Domain Model 변환
│               │   │   ├── IssueMapper.kt
│               │   │   └── ChatMapper.kt
│               │   └── repository/                 # Domain 인터페이스 구현체
│               │       ├── IssueRepositoryImpl.kt
│               │       └── ChatRepositoryImpl.kt
│               │
│               ├── presentation/
│               │   ├── dashboard/
│               │   │   ├── DashboardViewModel.kt
│               │   │   ├── DashboardState.kt
│               │   │   ├── DashboardIntent.kt
│               │   │   └── DashboardEffect.kt
│               │   └── chat/
│               │       ├── ChatViewModel.kt
│               │       ├── ChatState.kt
│               │       ├── ChatIntent.kt
│               │       └── ChatEffect.kt
│               │
│               └── di/                             # Koin 모듈 (인터페이스 ↔ 구현체 연결)
│                   ├── NetworkModule.kt
│                   ├── RepositoryModule.kt
│                   ├── UseCaseModule.kt
│                   └── ViewModelModule.kt
│
└── iosApp/
```

---

## DIP 적용 코드 예시

### Domain - Repository 인터페이스 (순수, 외부 의존 없음)
```kotlin
// shared/domain/repository/IssueRepository.kt
interface IssueRepository {
    suspend fun getIssues(): Result<List<Issue>>
    suspend fun getIssueDetail(id: String): Result<Issue>
}

// shared/domain/repository/ChatRepository.kt
interface ChatRepository {
    suspend fun sendMessage(sessionId: String, message: String): Result<ChatMessage>
    suspend fun getChatHistory(sessionId: String): Result<List<ChatMessage>>
}
```

### Domain - UseCase (인터페이스만 알고, 구현체 모름)
```kotlin
// shared/domain/usecase/GetIssuesUseCase.kt
class GetIssuesUseCase(
    private val repository: IssueRepository  // ← 인터페이스만 주입 (구현체 모름)
) {
    suspend operator fun invoke(): Result<List<Issue>> = repository.getIssues()
}
```

### Data - Repository 구현체 (Domain 인터페이스를 구현)
```kotlin
// shared/data/repository/IssueRepositoryImpl.kt
class IssueRepositoryImpl(
    private val api: IssueApi
) : IssueRepository {  // ← Domain 인터페이스 구현 (DIP)
    override suspend fun getIssues(): Result<List<Issue>> =
        runCatching { api.getIssues().map { it.toDomain() } }

    override suspend fun getIssueDetail(id: String): Result<Issue> =
        runCatching { api.getIssueDetail(id).toDomain() }
}
```

### Koin - DI 모듈 (인터페이스 ↔ 구현체 연결)
```kotlin
// shared/di/NetworkModule.kt
val networkModule = module {
    single {
        HttpClient {
            install(ContentNegotiation) { json() }
        }
    }
    single { IssueApi(get()) }
    single { ChatApi(get()) }
}

// shared/di/RepositoryModule.kt
val repositoryModule = module {
    // 핵심: 인터페이스 요청 시 구현체 제공 (DIP 실현)
    single<IssueRepository> { IssueRepositoryImpl(get()) }
    single<ChatRepository> { ChatRepositoryImpl(get()) }
}

// shared/di/UseCaseModule.kt
val useCaseModule = module {
    factory { GetIssuesUseCase(get()) }
    factory { GetIssueDetailUseCase(get()) }
    factory { SendChatMessageUseCase(get()) }
    factory { GetChatHistoryUseCase(get()) }
}

// shared/di/ViewModelModule.kt
val viewModelModule = module {
    viewModel { DashboardViewModel(get()) }
    viewModel { ChatViewModel(get(), get()) }
}
```

### Koin 초기화 (Android)
```kotlin
// androidMain - TikiTalkaApp.kt
class TikiTalkaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@TikiTalkaApp)
            checkModules()  // 앱 시작 시 모든 DI 미리 검증 (개발 중 크래시로 조기 발견)
            modules(
                networkModule,
                repositoryModule,
                useCaseModule,
                viewModelModule
            )
        }
    }
}
```

---

## MVI 패턴

```
User Action → Intent → ViewModel → State (UI 렌더링)
                                 ↓
                               Effect (일회성: 네비게이션, 토스트 등)
```

### 대시보드 예시
```kotlin
// DashboardState.kt
data class DashboardState(
    val issues: List<Issue> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

// DashboardIntent.kt
sealed class DashboardIntent {
    data object LoadIssues : DashboardIntent()
    data class SelectIssue(val issueId: String) : DashboardIntent()
    data object Refresh : DashboardIntent()
}

// DashboardEffect.kt
sealed class DashboardEffect {
    data class NavigateToChat(val issueId: String) : DashboardEffect()
    data class ShowError(val message: String) : DashboardEffect()
}

// DashboardViewModel.kt
class DashboardViewModel(
    private val getIssues: GetIssuesUseCase  // UseCase만 알고 Repository 모름
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state.asStateFlow()

    private val _effect = Channel<DashboardEffect>()
    val effect = _effect.receiveAsFlow()

    fun handleIntent(intent: DashboardIntent) {
        when (intent) {
            is DashboardIntent.LoadIssues -> loadIssues()
            is DashboardIntent.SelectIssue -> navigateToChat(intent.issueId)
            is DashboardIntent.Refresh -> loadIssues()
        }
    }

    private fun loadIssues() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            getIssues()
                .onSuccess { issues ->
                    _state.update { it.copy(issues = issues, isLoading = false) }
                }
                .onFailure { error ->
                    _state.update { it.copy(isLoading = false) }
                    _effect.send(DashboardEffect.ShowError(error.message ?: "알 수 없는 오류"))
                }
        }
    }

    private fun navigateToChat(issueId: String) {
        viewModelScope.launch {
            _effect.send(DashboardEffect.NavigateToChat(issueId))
        }
    }
}
```

---

## 네트워크 (Ktor)

### Base URL
```
개발: http://localhost:8080
운영: https://api.tikitalka.com (추후)
```

### 주요 API 엔드포인트
```
GET  /api/news                             # 화제성 뉴스 리스트 (tag, page, size, sort 쿼리 파라미터)
GET  /api/news/{id}                        # 뉴스 상세
POST /api/chat/message                     # 채팅 메시지 전송 (deviceId, message)
GET  /api/chat/history/{deviceId}          # 대화 히스토리
```

---

## 의존성 (libs.versions.toml)

```toml
[versions]
kotlin = "2.0.x"
compose-multiplatform = "1.7.x"
ktor = "3.x.x"
koin = "4.x.x"
kotlinx-coroutines = "1.x.x"
kotlinx-serialization = "1.x.x"
coil = "3.x.x"

[libraries]
# Ktor
ktor-client-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }
ktor-client-android = { module = "io.ktor:ktor-client-android", version.ref = "ktor" }
ktor-client-darwin = { module = "io.ktor:ktor-client-darwin", version.ref = "ktor" }
ktor-client-content-negotiation = { module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }
ktor-serialization-kotlinx-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }

# Koin
koin-core = { module = "io.insert-koin:koin-core", version.ref = "koin" }
koin-android = { module = "io.insert-koin:koin-android", version.ref = "koin" }
koin-compose = { module = "io.insert-koin:koin-compose", version.ref = "koin" }

# Kotlinx
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "kotlinx-coroutines" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "kotlinx-serialization" }

# Coil (이미지 로딩)
coil-compose = { module = "io.coil-kt.coil3:coil-compose", version.ref = "coil" }
coil-network-ktor = { module = "io.coil-kt.coil3:coil-network-ktor3", version.ref = "coil" }
```

---

## 개발 규칙

### 브랜치 전략
```
main      → 데모/배포용
dev       → 개발 통합
feature/* → 기능 개발
```

### 브랜치 네이밍
```
feature/mvi-setup
feature/koin-di
feature/network-ktor
feature/dashboard-ui
feature/chat-ui
feature/data-binding
```

### 커밋 컨벤션
```
feat: 새로운 기능
fix: 버그 수정
refactor: 리팩토링
chore: 빌드/설정 변경
style: UI/스타일 변경
```

### 코딩 규칙
- Domain 레이어는 순수 Kotlin만 사용 (Android, Ktor 등 외부 라이브러리 의존 금지)
- Repository는 반드시 인터페이스(Domain) → 구현체(Data) 구조 유지 (DIP)
- DTO와 Domain Model 반드시 분리, Mapper를 통해서만 변환
- `commonMain`에 최대한 코드 집중, 플랫폼별 코드 최소화
- State는 불변 data class, copy()로만 갱신
- ViewModel은 UseCase만 참조, Repository 직접 참조 금지

---

## 개발 로드맵 (10일)

| 단계 | 내용 |
|------|------|
| 1단계 | KMP 모듈 세팅, Koin DI 구성, Ktor 네트워크 기반 |
| 2단계 | Domain/Data 레이어 구현 (Repository + UseCase) |
| 3단계 | 대시보드 UI + MVI 상태 관리 + API 바인딩 |
| 4단계 | 채팅 UI + 티키타카 대화 흐름 구현 |
| 5단계 | Android/iOS 빌드 검증 및 UX 폴리싱 |

---

## 참고 자료
- [Kotlin Multiplatform 공식 문서](https://www.jetbrains.com/kotlin-multiplatform/)
- [Compose Multiplatform](https://www.jetbrains.com/lp/compose-multiplatform/)
- [Ktor Client](https://ktor.io/docs/client-create-multiplatform-application.html)
- [Koin KMP](https://insert-koin.io/docs/setup/koin#kotlin-multiplatform)
