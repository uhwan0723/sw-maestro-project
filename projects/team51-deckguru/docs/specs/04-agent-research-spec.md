# 04. Live Research Sub-graph — 외부 정보 수집 (ReAct)

> 담당: Agent 3 (Live Research / Tools)
> 범위: 외부 웹 정보 실시간 수집, 도구(웹검색/페이지/유튜브 자막), ReAct 루프, fact 추출 및 출처 추적, 도메인 화이트리스트
> 의존:
> - `02-agent-strategy-spec.md` (`need_live=true`일 때 호출되는 sub-graph)
> - `03-agent-rag-spec.md` (fact의 ground truth 매칭, promotion queue)

---

## 1. 책임 범위

| 포함 | 제외 |
|---|---|
| Live Research LangGraph sub-graph (ReAct) | 정적 RAG 인덱싱 (Agent2) |
| 웹검색 / 페이지 fetch / 유튜브 자막 도구 | LLM 자체 fine-tuning |
| Fact extraction LLM 호출 | UI |
| 도메인 화이트리스트 + robots.txt 검토 | HTTP 라우팅 |
| Promotion queue 적재 | Strategy 응답 합성 (Agent1) |

---

## 2. ReAct 루프 정의

LangGraph sub-graph로 구현. 최대 5 step.

```
[start] (input: question, extracted_keywords, patch_version)
    │
    ▼
[plan] ── 다음 어떤 도구를 어떤 query로 부를지 결정 (LLM, T=0)
    │
    ▼
[act]  ── plan의 tool 호출 (web_search / fetch_page / youtube_transcript)
    │
    ▼
[observe] ── 결과를 ReActLog에 기록 + 도메인 화이트리스트 검증
    │
    ▼
[reflect] ── 충분한 fact가 모였는가? (LLM, T=0)
    │
    ├── yes ──► [extract_facts] ──► [end]
    │
    └── no, step < 5 ──► [plan] (loop)
                  step >= 5 ──► [extract_facts] (timeout)
```

### 2.1 State

```python
class ResearchState(BaseModel):
    request_id: str
    patch_version: str
    question: str
    extracted_keywords: list[str]

    # ReAct trace
    react_log: list[ReActStep] = []
    step: int = 0

    # 누적 결과
    raw_observations: list[Observation] = []
    extracted_facts: list[WebFact] = []
    sources: list[Source] = []

    # 메타
    domains_visited: list[str] = []
    truncated: bool = False
    errors: list[str] = []

class ReActStep(BaseModel):
    step: int
    thought: str
    tool: Literal["web_search", "fetch_page", "youtube_transcript"]
    tool_input: dict
    observation_summary: str   # ≤200자

class Observation(BaseModel):
    tool: str
    url: str | None
    title: str | None
    text: str                  # 잘라낸 본문
    fetched_at: str            # ISO 8601

class WebFact(BaseModel):
    text: str                  # 핵심 사실 1~2문장
    quote: str                 # 원문 인용 (≤300자)
    source_url: str
    source_title: str | None
    published_at: str | None
    extraction_confidence: float  # 0~1
```

### 2.2 LangGraph node별 책임

| 노드 | LLM | 결정성 |
|---|---|---|
| `plan` | yes (small, T=0, structured: `{tool, tool_input, thought}`) | 부분 |
| `act` | no (도구 호출만) | 외부 의존 |
| `observe` | no (도메인 화이트리스트 + 본문 자르기) | 100% |
| `reflect` | yes (T=0, structured: `{enough: bool, reason: str}`) | 부분 |
| `extract_facts` | yes (T=0, structured: `list[WebFact]`) | 부분 |

---

## 3. 도구 (Tool) 정의

모두 결정적 함수 인터페이스. 외부 시점성으로 인해 결과는 시점별로 다를 수 있다 (불가피).

### 3.1 `web_search`

```python
async def web_search(query: str, *, k: int = 5) -> list[SearchResult]:
    """Tavily 또는 DuckDuckGo. 결과는 도메인 화이트리스트 외 자동 제외."""

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    published_at: str | None
```

| 항목 | 값 |
|---|---|
| 백엔드 | Tavily API (1차) / DuckDuckGo HTML (폴백) |
| Rate limit | 분당 30회 (Backend Semaphore로 강제) |
| Timeout | 5s |
| 도메인 필터 | `is_allowed_domain(url)` 통과한 것만 반환 |

### 3.2 `fetch_page`

```python
async def fetch_page(url: str) -> PageContent:
    """trafilatura로 본문 추출. JS rendering 없음 (MVP)."""

class PageContent(BaseModel):
    url: str
    title: str | None
    text: str            # ≤8000자, 초과 시 절단
    published_at: str | None
    fetched_at: str
```

| 항목 | 값 |
|---|---|
| 라이브러리 | `trafilatura` |
| Timeout | 8s |
| User-Agent | `DeckGuru/1.0 (research; +contact)` |
| robots.txt | 매번 검사. disallow → 403 raise |
| 본문 길이 | 8000자에서 절단 |

### 3.3 `youtube_transcript`

```python
async def youtube_transcript(video_id: str) -> Transcript:
    """youtube_transcript_api. 한국어 자막 우선, 없으면 영어."""

class Transcript(BaseModel):
    video_id: str
    text: str            # 전체 자막 합본 (≤10000자)
    language: str
    fetched_at: str
```

| 항목 | 값 |
|---|---|
| 라이브러리 | `youtube-transcript-api` |
| 채널 화이트리스트 | `04` §7 참조. 외부 채널은 거부. |
| Timeout | 6s |

---

## 4. ReAct 프롬프트 설계

### 4.1 `plan` 시스템 프롬프트 (요약)

```
당신은 롤토체스 정보 수집을 담당하는 Researcher입니다.

[목표]
사용자 질문에 답하기 위한 *최신 패치 정보*를 수집한다.
patch_version = {patch_version}

[사용 가능 도구]
- web_search(query: str, k: int=5)   ← 신선도 우선
- fetch_page(url: str)                ← search로 받은 URL 한정
- youtube_transcript(video_id: str)   ← 채널 화이트리스트 한정

[원칙]
- 한 번에 한 도구 호출.
- 같은 도구를 같은 입력으로 두 번 부르지 말 것.
- search 결과는 도메인 화이트리스트 외는 무시.
- 불필요하게 반복하지 말 것 — 충분한 fact가 모였으면 reflect=yes.

[출력]
JSON: {"thought": "...", "tool": "web_search", "tool_input": {"query": "TFT 14.9 메타 덱"}}
```

### 4.2 `reflect`

```
지금까지 수집한 사실로 사용자 질문에 답할 수 있는가?

질문: {question}
지금까지 fact:
{react_log_summary}

JSON: {"enough": bool, "reason": str}
```

### 4.3 `extract_facts`

```
다음 관찰들에서 사용자 질문에 답하기 위한 fact를 추출하라.

[원칙]
- 각 fact는 1~2문장. 출처 URL과 함께 반환.
- fact의 quote는 원문에서 그대로 인용 (≤300자).
- patch_version={patch_version} 기준 fact만 추출. 이전 patch 정보는 제외.
- extraction_confidence는 다음 룰:
  - 0.9: 단일 출처 + 명시적 수치/날짜 포함
  - 0.7: 단일 출처 + 정성 표현
  - 0.5: 단일 출처 + 모호함
  - 단일 출처는 최대 0.7로 cap

[출력]
JSON: list[{text, quote, source_url, source_title, published_at, extraction_confidence}]
```

---

## 5. 결정성 / 재현성

| 항목 | 보장 |
|---|---|
| 도구 호출 결과 | 외부 시점성 — 불가피. 7일 raw 캐시로 재현. |
| LLM 노드 (plan/reflect/extract) | T=0, structured, retry 1회 |
| 도메인 필터 / robots.txt | 결정적 |
| ReAct step 상한 | 5 — 무한 루프 방지 |

**캐싱:** 동일 `(tool, tool_input)` 호출은 7일간 SQLite 캐시. 디버깅과 회귀 테스트 골든셋 후보.

---

## 6. Promotion Queue (Live → Static RAG)

Live Research에서 추출한 `WebFact`는 즉시 RAG 인덱스에 들어가지 않는다(품질 위험). 대신 큐에 적재.

`backend/data/promotion_queue.jsonl`:
```json
{"queued_at":"2025-05-04T...","fact":{"text":"...","quote":"...","source_url":"...","extraction_confidence":0.9},"patch_version":"14.9","linked_index":"deck_templates"}
```

수동 검토 → Agent2의 ingest 파이프라인으로 인덱싱. **MVP는 적재만 하고 검토/인덱싱은 미포함.**

---

## 7. 도메인 화이트리스트 + 법적 검토

### 7.1 화이트리스트 (수정은 PR 필수)

`backend/app/research/whitelist.yaml`:
```yaml
allowed_domains:
  # 공식
  - teamfighttactics.leagueoflegends.com
  - oce.leagueoflegends.com
  - na.leagueoflegends.com

  # 메타 통계 (사전 합의 + ToS 검토)
  - lolchess.gg
  - tactics.tools
  - metatft.com

  # 한국 커뮤니티 (인용 명시)
  - inven.co.kr   # 인벤 — 게시판 인용 시 출처 명시 필수

allowed_youtube_channels:
  - "UC_xxxx_official"   # 사전 합의된 한국 TFT 채널 (3~5개, 4/29 결정)

forbidden_keywords_in_url:
  - "/login"
  - "/api/"
  - "/admin"
```

### 7.2 robots.txt 검사

```python
async def is_allowed_url(url: str) -> bool:
    domain = urlparse(url).netloc
    if domain not in WHITELIST.allowed_domains:
        return False
    rp = await _get_cached_robots(domain)
    return rp.can_fetch("DeckGuru/1.0", url)
```

robots.txt는 도메인당 24h 캐시.

### 7.3 4/29까지 처리할 작업 (Agent3 담당)

- [ ] lolchess.gg, tactics.tools, metatft.com의 ToS 확인 → 허용/금지 여부
- [ ] 인벤 게시판 인용 정책 확인
- [ ] 한국 TFT 유튜브 채널 3~5개 선정 (사전 동의 또는 자막 인용 정책)
- [ ] Tavily API 키 발급 (또는 DuckDuckGo HTML 폴백 검증)

---

## 8. 인터페이스 — Strategy Agent와의 계약

```python
# backend/app/research/api.py
async def run_live_research(
    request_id: str,
    *,
    question: str,
    extracted_keywords: list[str],
    patch_version: str,
    max_steps: int = 5,
    timeout_s: float = 15.0,
) -> ResearchResult:
    """Strategy Agent의 live_research 노드가 호출."""

class ResearchResult(BaseModel):
    facts: list[WebFact]
    sources: list[Source]
    react_steps: int
    domains_visited: list[str]
    truncated: bool
    latency_ms: int
```

타임아웃 초과 → `truncated=True` + 부분 결과. 예외 throw 안 함 (Strategy가 graceful degrade).

---

## 9. 디렉토리 구조

```
backend/app/research/
├── __init__.py
├── api.py                        # run_live_research
├── graph.py                      # LangGraph sub-graph
├── state.py                      # ResearchState
├── nodes/
│   ├── plan.py
│   ├── act.py
│   ├── observe.py
│   ├── reflect.py
│   └── extract_facts.py
├── tools/
│   ├── web_search.py
│   ├── fetch_page.py
│   └── youtube_transcript.py
├── whitelist.py                  # YAML 로드 + is_allowed_url
├── whitelist.yaml
├── cache.py                      # SQLite 7일 raw 캐시
└── promotion_queue.py
```

---

## 10. 평가

| 지표 | 측정 | 목표 |
|---|---|---|
| Live trigger 정확도 | 골든셋 중 freshness 키워드 포함 query에서 trigger 비율 | ≥ 90% |
| Source diversity | 한 응답 내 distinct domain 수 | ≥ 2 |
| extraction_confidence 평균 | extract_facts 출력 평균 | ≥ 0.7 |
| Latency P95 | trigger → result | ≤ 12s |
| robots.txt 위반 | 0 | 0 (assert) |

---

## 11. 기획서 피드백

| # | 기획서 | 문제 | 본 spec |
|---|---|---|---|
| 1 | "공식 패치 노트, 커뮤니티, 유튜브"(§4.1.2) | 어떤 사이트인지 미정. ToS 검토 부재 | §7 화이트리스트 + 4/29 검토 작업 |
| 2 | "BeautifulSoup / Playwright"(§4.1.2) | Playwright는 무거움. 정적 페이지면 trafilatura 충분 | §3.2 trafilatura 채택. JS rendering은 MVP 제외 |
| 3 | "최신 정보 수집"(§2.2.1) — 항상 호출? | LLM/네트워크 비용 큼 | §2 `need_live` 조건부 트리거 (RAG fail or freshness 키워드) |
| 4 | "정보 수집 → RAG 검색 → 메타 분석" 순차(§2.2 표) | 정보 부족 시에도 무조건 호출이면 비효율 | LangGraph 조건부 분기로 비용 절약 |
| 5 | 출처 추적 | 응답에 출처 표기만 있고 실제 fact-source 매핑 룰 없음 | §2.1 `WebFact.source_url` 1:1 + `extraction_confidence` 룰 |
| 6 | "환각 방지"(§1.4) | LLM이 fact를 만들어낼 위험 | §4.3 prompt에 "원문 인용" 강제 + Strategy의 verify_grounding 다층 |
| 7 | YouTube Transcript API(§4.1.2) | 어떤 채널? 저작권? | §7.1 화이트리스트 + 4/29 합의 |
| 8 | 비용 / 일일 한도 | 미언급 | §3.1 rate limit + Backend Semaphore + Live Research 일일 호출 한도 (선택) |
