# Demo QA Report

## Commands

- `python3 scripts/validate_harness.py` - pass
- `uv run --python 3.11 pytest` - pass, 109 passed
- `git diff --check` - pass
- `.env` loaded in-process + `generate_visit_guide("워터밤")` - pass
- `.env` loaded in-process + FastAPI `TestClient` smoke for `/health` and `/guides` - pass
- KOPIS key injected through hidden stdin/env + `generate_visit_guide("EK 콘서트")` - pass
- KOPIS key injected through hidden stdin/env + `generate_visit_guide("워터밤")` - pass
- KOPIS canonical HTTPS endpoint smoke - pass
- KOPIS key injected through hidden stdin/env + alias-expanded `search_kopis_with_fallback("랩비트 페스티벌")` - pass, no current KOPIS result
- Unit scenarios for official SNS notice, generic SNS post, and fan/review SNS post classification - pass
- Unit scenario for `threads.com` SNS classification - pass
- Review regression: lower-confidence SNS/review evidence does not fill fields on higher-confidence event info - pass
- Live multi-concert smoke with Tavily+Gemini and KOPIS configured through runtime env: `랩비트 페스티벌`, `워터밤`, `EK 콘서트`, `아이유 콘서트 KSPO`, `데이식스 콘서트`, `싸이 흠뻑쇼` - pass
- KOPIS-backed `워터밤` duplicate-merge regression smoke - pass
- Extra live examples with Tavily+Gemini and KOPIS configured through runtime env: `세븐틴 콘서트`, `에스파 콘서트`, `블랙핑크 콘서트`, `뮤지컬 알라딘`, `서울재즈페스티벌`, `펜타포트 락 페스티벌` - pass
- KOPIS-backed `서울재즈페스티벌` venue suffix cleanup smoke - pass
- Unit scenarios for public review/SNS tip queries, TikTok tip classification, and `후기 참고:` tip injection - pass
- Live review-tip smoke with Tavily+Gemini and KOPIS configured through runtime env: `KSPO DOME 스탠딩`, `YES24 Live Hall 물품보관`, `워터밤 준비물 꿀팁` - pass
- Performance-name-only review-tip smoke with Tavily+Gemini and KOPIS configured through runtime env: `워터밤`, `세븐틴 콘서트` - pass
- Review-tip cap/dedupe regression for LLM output - pass
- Unit cache scenarios for public search, KOPIS, Gemini provider calls, concurrent same-key calls, and uncached provider failures - pass
- Repeated live `워터밤` smoke in one process - pass, first run about 16.21s and second cached run about 0.00s

## Scenarios

| ID | Input | Result | Notes |
| --- | --- | --- | --- |
| S12 | `워터밤` | `event_candidates` | 실제 Tavily 검색 기준 2026 서울/부산 후보 반환, 과거 회차 후보 제거 |
| live | `워터밤` | `event_candidates` | 잘못된 `고양` 지역 후보 제거 확인, 서울/부산 후보만 노출 |
| KOPIS | `워터밤` | `event_candidates` | 실제 KOPIS 기준 서울/속초 후보 반환, 각 후보 `official_confirmed`, 서울 중복 후보 병합 확인 |
| S1/S10 | `KSPO DOME 콘서트 준비물` | `concert_with_venue_hint` | backend API에서 KSPO DOME venue guide 반환 |
| broad event | `랩비트 공연` | `event_candidates` | backend API에서 후보 4개 반환 |
| broad event | `랩비트 페스티벌` | `event_candidates` | backend API에서 2026 서울/문화비축기지 후보 반환, 과거 회차 후보 제거 |
| single concert | `EK 콘서트` | `concert_with_inferred_venue` + `event_info` | backend API에서 YES24 Live Hall, `2026.05.10`, `18:00` 표시 |
| live | `EK 콘서트` | `concert_with_inferred_venue` + `event_info` | 실제 Tavily+Gemini 기준 YES24 Live Hall, `2026.05.10` 표시 |
| live | `아이유 콘서트 KSPO` | `concert_with_venue_hint` | 과거 2019 공연 일정을 단일 공연 정보로 표시하지 않음 |
| live | `데이식스 콘서트` | `concert_with_inferred_venue` | 과거 날짜 공연 정보를 단일 공연 정보로 표시하지 않음 |
| live | `싸이 흠뻑쇼` | `unsupported_or_ambiguous` | 연도 없는 검색에서 2025 지역 후보를 제거하고 확정 후보로 강제하지 않음 |
| KOPIS | `EK 콘서트` | `concert_with_inferred_venue` + `event_info` | 실제 KOPIS 기준 YES24 Live Hall, `2026년 5월 10일`, `official_confirmed` |
| KOPIS alias | `랩비트 페스티벌` | no KOPIS result | `RAPBEAT`/`RAP BEAT` alias까지 검색했지만 현재 KOPIS 공식 목록 결과 없음 |
| live extra | `세븐틴 콘서트` | `event_candidates` | 공개검색 기준 인천 후보와 날짜/장소 노출, KOPIS 직접 매칭은 없음 |
| live extra | `에스파 콘서트` | `event_candidates` | 서울/2026 수준의 약한 후보만 확인되어 최신 공식 확인 필요 |
| live extra | `블랙핑크 콘서트` | `unsupported_or_ambiguous` | 현재 입력만으로는 확정 후보를 만들지 않고 추가 정보가 필요한 상태 유지 |
| live extra | `뮤지컬 알라딘` | `event_candidates` | 여러 지역 후보를 반환, 광역 공연/투어형 입력은 사용자가 지역·날짜를 고르는 흐름이 필요 |
| live extra | `서울재즈페스티벌` | `event_candidates` | KOPIS 공식 후보 반환, `올림픽공원 티켓` venue suffix 정제 및 중복 병합 확인 |
| live extra | `펜타포트 락 페스티벌` | `event_candidates` | KOPIS 기준 인천/송도달빛축제공원 공식 후보 반환 |
| SNS source | `랩비트 페스티벌 공식 SNS 공지` | `latest_official_check_required` | 공개 검색 결과의 공식 SNS 공지는 후보 추론에 사용하되 공식 확정으로 과승격하지 않음 |
| review tip | `KSPO DOME 스탠딩` | `venue_with_detail_question` | 후기/SNS 검색 결과가 있을 때 `후기 참고:` 입장 대기·물품보관 팁을 추가 |
| review tip | `YES24 Live Hall 물품보관` | `venue_with_detail_question` | 물품보관·퇴장·준비물 후기 팁을 참고용으로 추가 |
| review tip | `워터밤 준비물 꿀팁` | `unsupported_or_ambiguous` | 공식 후보를 강제하지 않고 후기 기반 준비물/물품보관/퇴장/입장 팁 4개만 표시 |
| review tip | `워터밤` | `event_candidates` | 공연명만 입력해도 후보와 후기 기반 준비물/퇴장/물품보관/입장 팁을 같이 표시 |
| review tip | `세븐틴 콘서트` | `concert_with_inferred_venue` | 공연명만 입력해도 MVP 공연장 추론 결과와 후기 기반 꿀팁을 같이 표시 |
| cache | repeated/concurrent provider calls | cached provider result | 같은 query/provider 설정에서 public search, KOPIS, Gemini 호출이 한 번만 실행되고, 같은 key의 동시 요청도 factory를 한 번만 실행하는지 단위 테스트로 확인 |
| cache | repeated `워터밤` | cached guide provider inputs | 같은 프로세스에서 두 번째 호출이 외부 provider 재호출 없이 즉시 반환됨 |

## Risks

- 라이브 검색 결과는 Tavily 색인 상태에 따라 후보 개수와 세부 후보명이 달라질 수 있습니다.
- KOPIS에 없는 공연명은 기존 public search/fallback 경로에 의존합니다.
- KOPIS 인증키는 커밋 대상 파일에 저장하지 않고 런타임 환경변수로만 주입했습니다.
- 뮤지컬·투어형 공연처럼 동일 이름의 지역 공연이 많은 입력은 후보 선택 UI가 중요합니다.
- SNS 검색 결과는 검색 snippet 품질에 의존하므로 공식 확인 채널로만 사용합니다.
- 인메모리 캐시는 프로세스 재시작 시 초기화되며, 여러 서버 인스턴스 간 공유 캐시는 아직 없습니다.
