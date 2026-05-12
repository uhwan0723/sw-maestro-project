# Clean Architecture + MVI 레퍼런스

## 레이어 체크리스트

### Domain 레이어 작성 전 확인
- [ ] 외부 라이브러리 import 없음 (순수 Kotlin만)
- [ ] Repository는 interface만 정의, 구현체 없음
- [ ] UseCase는 단일 책임 (invoke 하나)
- [ ] Model은 불변 data class

### Data 레이어 작성 전 확인
- [ ] DTO ↔ Domain Model 변환은 Mapper에서만
- [ ] Repository 구현체는 Domain interface를 implement
- [ ] API 호출 결과는 반드시 `runCatching`으로 감싸서 Result 반환
- [ ] DTO에 `@Serializable` 붙었는지 확인

### Presentation 레이어 작성 전 확인
- [ ] ViewModel은 UseCase만 참조 (Repository 직접 참조 금지)
- [ ] State는 불변 data class, `_state.update { it.copy(...) }`로만 갱신
- [ ] 일회성 이벤트(네비게이션, 토스트)는 Effect로 처리
- [ ] `viewModelScope.launch` 안에서 코루틴 실행

---

## MVI 구현 패턴

### State / Intent / Effect 분리 원칙
```
State  → UI가 렌더링하는 데이터 (항상 최신 상태)
Intent → 사용자 액션 또는 시스템 이벤트
Effect → 한 번만 발생하는 사이드 이펙트 (뒤로가기, 스낵바 등)
```

### ViewModel 구조 템플릿
```kotlin
class XxxViewModel(
    private val xxxUseCase: XxxUseCase
) : ViewModel() {

    private val _state = MutableStateFlow(XxxState())
    val state: StateFlow<XxxState> = _state.asStateFlow()

    private val _effect = Channel<XxxEffect>(Channel.BUFFERED)
    val effect = _effect.receiveAsFlow()

    fun handleIntent(intent: XxxIntent) {
        when (intent) {
            is XxxIntent.Yyy -> doYyy()
        }
    }
}
```

---

## 안티패턴 (하면 안 되는 것들)

### Domain 레이어 오염
```kotlin
// BAD: Domain에서 Ktor 의존
import io.ktor.client.HttpClient
class IssueRepository(val client: HttpClient)  // X

// GOOD: 순수 인터페이스만
interface IssueRepository {
    suspend fun getIssues(): Result<List<Issue>>
}
```

### ViewModel에서 Repository 직접 참조
```kotlin
// BAD
class DashboardViewModel(val repo: IssueRepositoryImpl)

// GOOD
class DashboardViewModel(val getIssues: GetIssuesUseCase)
```

### State를 직접 변경
```kotlin
// BAD
_state.value.issues.add(newIssue)  // 불변 위반

// GOOD
_state.update { it.copy(issues = it.issues + newIssue) }
```

### Effect 대신 State로 네비게이션 처리
```kotlin
// BAD: State로 네비게이션
data class DashboardState(val navigateToChatId: String? = null)

// GOOD: Effect로 네비게이션
sealed class DashboardEffect {
    data class NavigateToChat(val issueId: String) : DashboardEffect()
}
```

---

## 에러 처리 패턴

```kotlin
// UseCase에서 Result 그대로 전달
suspend operator fun invoke(): Result<List<Issue>> = repository.getIssues()

// ViewModel에서 onSuccess / onFailure 분기
getIssues()
    .onSuccess { issues ->
        _state.update { it.copy(issues = issues, isLoading = false) }
    }
    .onFailure { error ->
        _state.update { it.copy(isLoading = false) }
        _effect.send(DashboardEffect.ShowError(error.message ?: "알 수 없는 오류"))
    }
```
