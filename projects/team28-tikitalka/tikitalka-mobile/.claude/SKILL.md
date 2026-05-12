# TikiTalka Mobile - 프로젝트 스킬 정의

이 프로젝트에서 코드를 작성하거나 검토할 때 아래 레퍼런스를 참조한다.

---

## 1. Clean Architecture + MVI

@references/clean-arch-mvi.md

레이어 체크리스트, MVI 구현 패턴, 안티패턴, 에러 처리 패턴을 담고 있다.

**언제 참조하나:**
- Domain / Data / Presentation 레이어 코드 작성 시
- ViewModel, State, Intent, Effect 구현 시
- Repository 인터페이스 및 구현체 작성 시

---

## 2. KMP + CMP + Android

@references/kmp-cmp-android.md

소스셋 구조, expect/actual 패턴, Compose Multiplatform 주의사항, Koin 설정, Ktor 엔진 분리를 담고 있다.

**언제 참조하나:**
- commonMain / androidMain / iosMain 소스셋 결정 시
- 플랫폼별 구현 분기 (expect/actual) 작성 시
- Koin, Ktor, Coil 설정 시