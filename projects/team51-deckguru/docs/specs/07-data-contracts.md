# 07. Data Contracts — 단일 진실 소스

> 본 문서는 모든 역할이 공유하는 **JSON Schema / API 계약** 단일 진실 소스다.
> 변경 시 모든 담당자에게 PR 리뷰가 강제된다 (CODEOWNERS).
> Backend는 Pydantic v2, Frontend는 Zod로 본 문서 기반 코드 생성/수동 동기화.

## 목차

1. 공통 enum
2. 공통 객체 (Source / RagChunk / WebFact)
3. RAG 인덱스 행 schema (8 indices)
4. Strategy Agent 출력 — `RecommendationResponse`
5. Backend API 계약
6. 변경 관리 규칙

---

## 1. 공통 enum

### 1.1 `Tier`

```typescript
type Tier =
  | "IRON" | "BRONZE" | "SILVER" | "GOLD"
  | "PLATINUM" | "EMERALD" | "DIAMOND" | "MASTER+";
```

### 1.2 `PlayStyle`

```typescript
type PlayStyle =
  | "stable_top4"        // 안정적인 순방형 (꾸준히 4등 안)
  | "high_risk_first"    // 고점 높은 1등형
  | "easy_beginner"      // 쉬운 초보자형
  | "flexible";          // 유동적인 운영형
```

### 1.3 `Intent`

```typescript
type Intent =
  | "recommend_deck"     // 현재 패치 추천 덱
  | "deck_playstyle"     // 특정 덱 운영법
  | "item_pivot"         // 초반 아이템 기반 덱 추천
  | "patch_summary"      // 패치 노트 요약
  | "other";             // 지원 범위 외
```

### 1.4 `Phase`

```typescript
type Phase = "early" | "mid" | "late";
```

### 1.5 `Difficulty`

```typescript
type Difficulty = "easy" | "medium" | "hard";
```

### 1.6 `Confidence`

```typescript
type Confidence = "high" | "medium" | "low";
```

확신도 결정 룰 (Strategy Agent `verify_grounding` 노드, 결정적):

| 조건 | confidence |
|---|---|
| `len(filtered_decks) == 0` | `low` |
| `rag_avg_score >= 0.6 AND len(sources) >= 1` | `high` |
| 그 외 | `medium` |

### 1.7 `WarningCode`

응답 `warnings[]` 필드에 들어가는 정해진 코드. Frontend가 사용자 메시지로 매핑.

```typescript
type WarningCode =
  | "insufficient_data_after_patch"   // 패치 직후 통계 부족
  | "all_decks_filtered"              // grounding 검증으로 모두 제거
  | "research_truncated"              // Live Research 5 step / 15s 초과
  | "research_skipped_no_whitelist"   // 도메인 화이트리스트 위반으로 skip
  | "single_source"                   // 출처 1개만 (다양성 부족)
  | "deck_filtered_<name>_insufficient_units"  // 특정 deck이 화이트리스트 통과 후 unit 3개 미만
  | "rag_avg_score_low"               // RAG 매칭 score < 0.4
  | "patch_version_fallback";         // 현재 patch 데이터 없어 직전 patch 사용
```

### 1.8 `IndexName`

```typescript
type IndexName =
  | "units" | "traits" | "items" | "augments"
  | "deck_templates" | "playbook" | "patch_summary" | "glossary";
```

### 1.9 `ToolName` (Live Research)

```typescript
type ToolName = "web_search" | "fetch_page" | "youtube_transcript";
```

---

## 2. 공통 객체

### 2.1 `Source`

외부 출처 1개. `RecommendationResponse.sources[]` 와 `WebFact.source_*` 필드의 정합성을 보장한다.

```json
{
  "type": "object",
  "required": ["title", "url", "snippet"],
  "properties": {
    "title": { "type": "string", "minLength": 1 },
    "url":   { "type": "string", "format": "uri", "pattern": "^https?://" },
    "published_at": { "type": ["string", "null"], "format": "date-time" },
    "snippet": { "type": "string", "maxLength": 200 },
    "source_kind": {
      "enum": ["patch_note_official", "meta_site", "community_post", "youtube"],
      "description": "선택. 분석/평가 시 활용"
    }
  }
}
```

### 2.2 `RagChunk`

Strategy Agent와 Live Research가 RAG Service에서 받는 검색 결과 단일 항목.

```json
{
  "type": "object",
  "required": ["id", "index", "text", "metadata", "score"],
  "properties": {
    "id":       { "type": "string", "description": "sha256(name+patch)" },
    "index":    { "$ref": "#/$defs/IndexName" },
    "text":     { "type": "string" },
    "metadata": { "type": "object" },
    "score":    { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

### 2.3 `WebFact` (Live Research 출력)

```json
{
  "type": "object",
  "required": ["text", "quote", "source_url", "extraction_confidence"],
  "properties": {
    "text":  { "type": "string", "maxLength": 400, "description": "1~2 문장 fact" },
    "quote": { "type": "string", "maxLength": 300, "description": "원문 인용" },
    "source_url":   { "type": "string", "format": "uri" },
    "source_title": { "type": ["string", "null"] },
    "published_at": { "type": ["string", "null"], "format": "date-time" },
    "extraction_confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

### 2.4 `PlaybookStep`

```json
{
  "type": "object",
  "required": ["phase", "instruction"],
  "properties": {
    "phase": { "enum": ["early", "mid", "late"] },
    "instruction": { "type": "string", "minLength": 1, "maxLength": 200 }
  }
}
```

### 2.5 `DeckRecommendation`

응답의 핵심 객체. **`core_units`, `key_items`는 RAG 화이트리스트 통과한 이름만 허용** (Strategy `verify_grounding` 노드가 강제).

```json
{
  "type": "object",
  "required": [
    "name", "difficulty", "core_units", "key_items",
    "augment_direction", "playbook",
    "good_conditions", "avoid_conditions", "fallback_plan", "rationale"
  ],
  "properties": {
    "name": { "type": "string", "minLength": 1, "maxLength": 60 },
    "difficulty": { "enum": ["easy", "medium", "hard"] },
    "core_units": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 3, "maxItems": 9,
      "description": "RAG units 인덱스 화이트리스트 통과한 한국어 정자체 이름"
    },
    "key_items": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1, "maxItems": 6
    },
    "augment_direction": { "type": "string", "maxLength": 120 },
    "playbook": {
      "type": "array",
      "items": { "$ref": "#/$defs/PlaybookStep" },
      "minItems": 1
    },
    "good_conditions": {
      "type": "array",
      "items": { "type": "string", "maxLength": 80 },
      "minItems": 1
    },
    "avoid_conditions": {
      "type": "array",
      "items": { "type": "string", "maxLength": 80 }
    },
    "fallback_plan": { "type": "string", "maxLength": 200 },
    "rationale": { "type": "string", "maxLength": 300 }
  }
}
```

---

## 3. RAG 인덱스 행 schema (8 indices)

각 인덱스는 ChromaDB collection 1개. row schema는 ingest 단계의 검증에 사용.

### 3.1 `units`

```json
{
  "type": "object",
  "required": ["id", "name", "cost", "traits", "role", "patch_version", "text"],
  "properties": {
    "id":   { "type": "string", "pattern": "^u_[a-z_]+_[0-9.]+$" },
    "name": { "type": "string", "description": "한국어 정자체" },
    "cost": { "type": "integer", "minimum": 1, "maximum": 5 },
    "traits": { "type": "array", "items": { "type": "string" } },
    "role": { "enum": ["DPS", "Tank", "Bruiser", "Caster", "Support", "Utility"] },
    "image_url": { "type": ["string", "null"], "format": "uri" },
    "patch_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+$" },
    "text": { "type": "string", "description": "임베딩 대상 자연어 본문" }
  }
}
```

### 3.2 `traits`

```json
{
  "required": ["id", "name", "tiers", "synergy_summary", "patch_version", "text"],
  "properties": {
    "id":   { "type": "string", "pattern": "^t_[a-z_]+_[0-9.]+$" },
    "name": { "type": "string" },
    "tiers": { "type": "array", "items": { "type": "integer" }, "description": "[2,4,6] 같은 활성화 단계" },
    "synergy_summary": { "type": "string" },
    "patch_version": { "type": "string" },
    "text": { "type": "string" }
  }
}
```

### 3.3 `items`

```json
{
  "required": ["id", "name", "recipe", "effect", "tags", "patch_version", "text"],
  "properties": {
    "id":     { "type": "string", "pattern": "^i_[a-z_]+_[0-9.]+$" },
    "name":   { "type": "string" },
    "recipe": { "type": "string", "description": "조합식 (예: 'BF대검 + BF대검')" },
    "effect": { "type": "string" },
    "tags":   { "type": "array", "items": { "enum": ["AD","AP","Tank","Util","Support","Mana"] } },
    "recommended_for_units": { "type": "array", "items": { "type": "string" } },
    "patch_version": { "type": "string" },
    "text": { "type": "string" }
  }
}
```

### 3.4 `augments`

```json
{
  "required": ["id", "name", "tier", "effect", "patch_version", "text"],
  "properties": {
    "id":   { "type": "string", "pattern": "^a_[a-z_]+_[0-9.]+$" },
    "name": { "type": "string" },
    "tier": { "enum": ["silver", "gold", "prismatic"] },
    "effect": { "type": "string" },
    "synergy_decks": { "type": "array", "items": { "type": "string" } },
    "patch_version": { "type": "string" },
    "text": { "type": "string" }
  }
}
```

### 3.5 `deck_templates`

```json
{
  "required": ["id", "name", "core_units", "key_items", "difficulty",
               "preferred_styles", "patch_version", "text"],
  "properties": {
    "id":   { "type": "string", "pattern": "^d_[a-z0-9_]+_[0-9.]+$" },
    "name": { "type": "string" },
    "core_units": { "type": "array", "items": { "type": "string" }, "minItems": 3, "maxItems": 9 },
    "key_items":  { "type": "array", "items": { "type": "string" }, "minItems": 1, "maxItems": 6 },
    "augment_direction": { "type": "string" },
    "difficulty": { "enum": ["easy", "medium", "hard"] },
    "preferred_styles": {
      "type": "array",
      "items": { "enum": ["stable_top4", "high_risk_first", "easy_beginner", "flexible"] }
    },
    "tier_recommendation": {
      "type": "array",
      "items": { "enum": ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND","MASTER+"] }
    },
    "patch_version": { "type": "string" },
    "text": { "type": "string" }
  }
}
```

### 3.6 `playbook`

```json
{
  "required": ["id", "topic", "phase", "patch_version", "text"],
  "properties": {
    "id":    { "type": "string", "pattern": "^pb_[a-z_]+_[a-z]+$" },
    "topic": { "enum": ["level_up", "reroll", "economy", "health", "positioning"] },
    "phase": { "enum": ["early", "mid", "late"] },
    "patch_version": {
      "oneOf": [{ "type": "string" }, { "const": "all" }],
      "description": "패치 무관한 운영은 'all'"
    },
    "text": { "type": "string" }
  }
}
```

### 3.7 `patch_summary`

```json
{
  "required": ["id", "patch_version", "change_type", "target_kind", "target_name", "text"],
  "properties": {
    "id": { "type": "string", "pattern": "^ps_[0-9.]+_[0-9]+$" },
    "patch_version": { "type": "string" },
    "change_type": { "enum": ["buff", "nerf", "rework", "new", "removed", "system"] },
    "target_kind": { "enum": ["unit", "item", "trait", "augment", "system"] },
    "target_name": { "type": "string" },
    "text": { "type": "string", "description": "변경점 요약" }
  }
}
```

### 3.8 `glossary`

```json
{
  "required": ["id", "term", "patch_version", "text"],
  "properties": {
    "id":   { "type": "string", "pattern": "^g_[a-z_]+$" },
    "term": { "type": "string" },
    "aliases": { "type": "array", "items": { "type": "string" } },
    "patch_version": { "oneOf": [{ "type": "string" }, { "const": "all" }] },
    "text": { "type": "string" }
  }
}
```

---

## 4. Strategy Agent 출력 — `RecommendationResponse`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "request_id", "patch_version", "intent", "meta_summary",
    "decks", "sources", "confidence", "warnings", "generated_at"
  ],
  "properties": {
    "request_id":    { "type": "string", "format": "uuid" },
    "patch_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+$" },
    "intent": { "$ref": "#/$defs/Intent" },
    "meta_summary": {
      "type": "string",
      "maxLength": 400,
      "description": "현재 패치 메타 요약. intent=other 일 때는 '지원 범위 안내' 텍스트."
    },
    "decks": {
      "type": "array",
      "items": { "$ref": "#/$defs/DeckRecommendation" },
      "maxItems": 3,
      "description": "intent=other 또는 verify_grounding으로 모두 걸러진 경우 빈 배열."
    },
    "sources": {
      "type": "array",
      "items": { "$ref": "#/$defs/Source" },
      "description": "decks의 rationale에 인용된 모든 외부 사실의 출처. 1:1 대응 보장."
    },
    "confidence": { "$ref": "#/$defs/Confidence" },
    "warnings": {
      "type": "array",
      "items": { "type": "string" },
      "description": "WarningCode (§1.7) 또는 'deck_filtered_<name>_*' 형태의 동적 코드"
    },
    "generated_at": { "type": "string", "format": "date-time" },
    "debug": {
      "type": "object",
      "description": "선택 — DEMO_MODE=true일 때만 노출",
      "properties": {
        "react_steps": { "type": "integer", "minimum": 0, "maximum": 5 },
        "rag_avg_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "tier2_triggered": { "type": "boolean" },
        "node_latencies_ms": {
          "type": "object",
          "additionalProperties": { "type": "integer" }
        }
      }
    }
  }
}
```

### 4.1 응답 정합성 불변식 (invariants)

Strategy Agent의 `verify_grounding` + `format_response`가 **모두** 보장:

| # | 불변식 |
|---|---|
| I1 | `decks[*].core_units` 의 모든 원소는 RAG `units` 인덱스의 `name` 집합에 존재 |
| I2 | `decks[*].key_items` 의 모든 원소는 RAG `items` 인덱스의 `name` 집합에 존재 |
| I3 | `decks[*].rationale` 에 등장하는 수치는 `sources[*].snippet` 또는 RAG chunk text에서 출처 추적 가능 |
| I4 | `len(decks) == 0` ⇔ `confidence == "low"` (역도 강제) |
| I5 | `confidence == "high"` ⇒ `len(sources) >= 1` |
| I6 | `intent == "other"` ⇒ `len(decks) == 0 AND meta_summary` 이 안내 문구 |
| I7 | `intent == "patch_summary"` ⇒ `meta_summary` 길이 ≥ 100자 |
| I8 | `len(decks) > 0` ⇒ 모든 deck의 `playbook[]` 에 `phase` 가 최소 1개 (early/mid/late 중 하나) 존재 |
| I9 | `sources[*].url` 은 모두 도메인 화이트리스트(`04-agent-research-spec.md` §7.1) 통과 |
| I10 | `patch_version` 은 응답 시점의 ENV `PATCH_VERSION` 와 일치 |

CI test (`tests/test_invariants.py`)가 골든셋 응답에 대해 위 10개를 assert.

---

## 5. Backend API 계약

### 5.1 `POST /api/recommend`

**Request:**

```json
{
  "tier": "GOLD",
  "play_style": "stable_top4",
  "question": "현재 패치에서 골드가 티어 올리기 좋은 덱 3개 추천해줘"
}
```

| 필드 | 타입 | 필수 | 검증 |
|---|---|---|---|
| `tier` | `Tier` enum | yes | §1.1 |
| `play_style` | `PlayStyle` enum | yes | §1.2 |
| `question` | string | yes | 1 ≤ len ≤ 500 |

Pydantic v2 모델 (`backend/app/schemas/api.py`):
```python
class RecommendRequest(BaseModel):
    tier: Tier
    play_style: PlayStyle
    question: str = Field(min_length=1, max_length=500)
```

**Response 200:** `RecommendationResponse` (§4)

**Response Headers:**
- `X-Request-ID: <uuid>`
- `X-Cache: HIT|MISS`
- `X-Patch-Version: 14.9`

**Errors:** §3.7 in `05-backend-spec.md`

### 5.2 `GET /api/health`

```json
{
  "status": "ok",
  "patch_version": "14.9",
  "rag_chunks": {
    "units": 60, "traits": 24, "items": 28, "augments": 92,
    "deck_templates": 18, "playbook": 24, "patch_summary": 32, "glossary": 41
  },
  "uptime_s": 3601
}
```

| 필드 | 비고 |
|---|---|
| `status` | `"ok"` 또는 `"degraded"`. 어떤 collection이 0 → degraded |
| `rag_chunks` | 각 인덱스의 chunk count (모니터링용) |

### 5.3 `GET /api/patch-info`

```json
{
  "patch_version": "14.9",
  "last_updated": "2025-05-04T03:00:00Z",
  "warnings": []
}
```

| 필드 | 비고 |
|---|---|
| `last_updated` | RAG 빌드 완료 timestamp |
| `warnings` | 가능 값: `["data_may_be_insufficient_after_patch"]` (patch_age_days ≤ 1) |

### 5.4 `POST /api/feedback`

**Request:**
```json
{
  "request_id": "uuid-...",
  "rating": 4,
  "comment": "운영법이 도움됐어요",
  "deck_clicked": "9코스트 정밀"
}
```

| 필드 | 타입 | 필수 |
|---|---|---|
| `request_id` | uuid | yes |
| `rating` | integer 1~5 | yes |
| `comment` | string ≤ 500 | no |
| `deck_clicked` | string | no |

**Response 200:**
```json
{ "ok": true }
```

### 5.5 `GET /api/example-questions`

```json
[
  {"intent": "recommend_deck", "text": "..."},
  {"intent": "deck_playstyle", "text": "..."},
  {"intent": "item_pivot",     "text": "..."},
  {"intent": "patch_summary",  "text": "..."}
]
```

### 5.6 에러 응답 (공통)

```json
{
  "error": {
    "code": "agent_timeout",
    "message": "응답이 너무 오래 걸려요. 다시 시도하시거나 더 짧은 질문을 입력해주세요.",
    "request_id": "uuid-..."
  }
}
```

| code | HTTP | 의미 |
|---|---|---|
| `validation_error` | 400 | Pydantic 검증 실패 |
| `intent_unsupported` | 422 | Agent intent=other |
| `rate_limited` | 429 | IP 분당/시간당 한도 초과 |
| `agent_internal` | 500 | Agent 내부 예외 |
| `rag_unavailable` | 502 | ChromaDB 접근 실패 |
| `agent_failed` | 502 | LLM schema fail 2회 연속 |
| `agent_timeout` | 504 | 25s 초과 |

---

## 6. 변경 관리 규칙

1. **본 문서가 schema 단일 진실 소스다.**
2. Backend는 Pydantic 모델을, Frontend는 Zod 스키마를 본 문서 기반으로 유지한다.
   - MVP는 수기 동기. 시간 남으면 `pydantic-to-zod` / `datamodel-code-generator` 자동화.
3. 필드 추가는 backward-compatible 하게 (선택 필드 기본값).
4. enum 변경은 모든 담당자에게 PR 리뷰 강제 (CODEOWNERS).
5. `decks` schema 변경은 Strategy Agent + Frontend `<DeckCard />` + 평가 골든셋이 동일 PR에 포함되어야 머지 가능.
6. `Intent` enum 추가는 Strategy `analyze_intent` few-shot + RAG query plan + Frontend `ExampleChips`가 동일 PR.
7. `WarningCode` 추가는 Frontend `lib/warnings.ts` 매핑이 동일 PR.
8. 본 문서의 examples는 `tests/fixtures/contract_examples/` 에서 로드되어 schema validation을 통과해야 한다 (CI). 실제 fixture 파일이 본 문서의 모든 schema에 대해 1개 이상 존재.

### 6.1 자동화 검증 (CI)

```python
# tests/test_contracts.py
from jsonschema import validate

@pytest.mark.parametrize("name,schema,fixture", load_contract_pairs())
def test_fixture_matches_schema(name, schema, fixture):
    validate(instance=fixture, schema=schema)
```

`load_contract_pairs`는 `07-data-contracts.md`에서 schema를 추출하고 `tests/fixtures/contract_examples/<name>.json`을 매칭. 둘 중 하나만 있으면 fail.

### 6.2 호환성 매트릭스

| 변경 종류 | Backend | Frontend | Agent | 마이그레이션 |
|---|---|---|---|---|
| 필드 추가 (optional) | ✅ | ✅ (무시) | ✅ | 무 |
| 필드 추가 (required) | ⚠ deploy 순서 | ⚠ | ⚠ | Backend → Agent → Frontend |
| 필드 제거 | ⚠ | ⚠ | ⚠ | 모두 동시 |
| enum 추가 | ✅ | ✅ (Frontend가 unknown 처리) | ✅ | 무 |
| enum 제거 | ⚠ | ⚠ | ⚠ | 모두 동시 |
| 의미 변경 | 🚫 | 🚫 | 🚫 | 새 필드로 |

### 6.3 버저닝

MVP는 단일 버전. v2부터는 `/api/v2/recommend` 같은 path 기반 버저닝. 본 문서의 schema는 항상 v1.
