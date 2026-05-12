# KMP + CMP + Android 레퍼런스

## 소스셋 구조 원칙

```
commonMain   → 비즈니스 로직, UI, Domain, Data 전부 여기에 최대한 집중
androidMain  → Android 전용 API (Context, Activity 등) 사용할 때만
iosMain      → iOS 전용 API 사용할 때만
```

### 플랫폼 코드 최소화 체크리스트
- [ ] 구현이 commonMain에 가능한가? → 가능하면 commonMain에
- [ ] Android/iOS 둘 다 필요한가? → `expect/actual` 사용
- [ ] 한 플랫폼만 필요한가? → 해당 플랫폼 소스셋에만 작성

---

## expect / actual 패턴

### 사용 시점
플랫폼마다 구현이 다른 코드 (예: 날짜 포맷, 로컬 스토리지, 권한 등)

```kotlin
// commonMain
expect fun getPlatformName(): String

// androidMain
actual fun getPlatformName(): String = "Android"

// iosMain
actual fun getPlatformName(): String = "iOS"
```

### ViewModel expect/actual (KMP + lifecycle-viewmodel)
```kotlin
// commonMain - ViewModel은 androidx.lifecycle 사용 (KMP 지원)
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope

class DashboardViewModel : ViewModel() {
    // viewModelScope는 commonMain에서 바로 사용 가능
}
```

---

## Compose Multiplatform 주의사항

### Composable 함수 네이밍
ktlint `function-naming` 규칙 비활성화 중 (`.editorconfig` 설정됨)
→ `DashboardScreen()`, `ChatScreen()` 등 PascalCase 사용 정상

### Preview
```kotlin
// Android에서만 Preview 동작
@Composable
@Preview  // android.tooling.preview.Preview
fun DashboardScreenPreview() {
    DashboardScreen()
}
```

### 이미지 로딩 (Coil3)
```kotlin
// commonMain에서 사용 가능 (coil3 + ktor 연동)
AsyncImage(
    model = imageUrl,
    contentDescription = null,
)
```

---

## Koin KMP 설정 주의사항

### iOS에서 Koin 초기화
```swift
// iosApp/iOSApp.swift
@main
struct iOSApp: App {
    init() {
        KoinInitKt.doInitKoin()  // Koin 초기화 필수
    }
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### commonMain에서 ViewModel 주입
```kotlin
// Compose에서 koin-compose 사용
val viewModel: DashboardViewModel = koinViewModel()
```

---

## Ktor Client 플랫폼별 엔진

```kotlin
// androidMain
actual fun createHttpClient() = HttpClient(Android) { ... }

// iosMain
actual fun createHttpClient() = HttpClient(Darwin) { ... }
```

단, `commonMain`에서 `HttpClient()`로 공통 설정 후 플랫폼 엔진만 분리하는 패턴 권장:
```kotlin
// commonMain/di/NetworkModule.kt
val networkModule = module {
    single {
        HttpClient {
            install(ContentNegotiation) {
                json(Json { ignoreUnknownKeys = true })
            }
            install(Logging) {
                level = LogLevel.INFO
            }
            defaultRequest {
                url("http://localhost:8080")
            }
        }
    }
}
```

---

## 빌드 관련

### Android 빌드
```bash
./gradlew :composeApp:assembleDebug
./gradlew :composeApp:installDebug
```

### iOS 빌드
Xcode에서 `iosApp/iosApp.xcodeproj` 열어서 빌드
또는 KMM Plugin으로 IDE에서 직접 실행

### ktlint
```bash
./gradlew ktlintCheck    # 검사
./gradlew ktlintFormat   # 자동 수정
```