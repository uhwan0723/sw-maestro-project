# 03. RAG Service — 인덱싱 / 검색 / Grounding

> 담당: Agent 2 (RAG / Data)
> 범위: 데이터 수집(정적) → 정규화 → chunking → 임베딩 → ChromaDB 저장, 검색 API, whitelist API
> 의존:
> - `07-data-contracts.md` (RagChunk, GarmentSlot 유사한 enum / 인덱스 schema)
> - `04-agent-research-spec.md`의 동적 chunk promotion 인터페이스 (live → static 승격)

---

## 1. 책임 범위

| 포함 | 제외 |
|---|---|
| 8개 ChromaDB 인덱스 정의 + 임베딩 파이프라인 | LangGraph 노드 작성 (Agent1) |
| 정적 데이터 수집 스크립트 (공식 패치 노트, 데이터 시트) | 실시간 웹검색 (Agent3) |
| chunking 전략 + 메타데이터 | LLM 호출 |
| 검색 API (`search`, `multi_search`) | UI |
| whitelist API (`get_whitelist`) | API HTTP |
| patch_version 갱신 / 재인덱싱 / 마이그레이션 | |
| Live Research가 추출한 fact의 동적 chunk 승격 처리 | |

---

## 2. 인덱스 정의 (8개)

| 인덱스 | 1 chunk = ? | chunking | 임베딩 모델 | 메타데이터 (필수) |
|---|---|---|---|---|
| `units` | 기물 1개 | 분할 X | `bge-m3` | `name, cost (1~5), traits[], role, image_url, patch_version` |
| `traits` | 특성 1개 | 분할 X | `bge-m3` | `name, tiers[] ([2,4,6] 등), synergy_summary, patch_version` |
| `items` | 아이템 1개 | 분할 X | `bge-m3` | `name, recipe (string), effect, tags[] (AD/AP/Tank/Util), recommended_for_units[], patch_version` |
| `augments` | 증강체 1개 | 분할 X | `bge-m3` | `name, tier (silver/gold/prismatic), effect, synergy_decks[], patch_version` |
| `deck_templates` | 덱 1개 | 분할 X | `bge-m3` | `name, core_units[], key_items[], augment_direction, difficulty (easy/medium/hard), preferred_styles[], patch_version` |
| `playbook` | 토픽 1개 | 섹션 단위 (≤500자) | `bge-m3` | `topic (level_up/reroll/economy/health), phase (early/mid/late), patch_version` |
| `patch_summary` | 변경점 1개 | 분할 X | `bge-m3` | `patch_version, change_type (buff/nerf/rework/new), target_kind (unit/item/trait/augment/system), target_name` |
| `glossary` | 용어 1개 | 분할 X | `bge-m3` | `term, aliases[], patch_version (또는 "all")` |

> **patch_version은 모든 인덱스의 1급 메타데이터**다. 검색 시 `where={"patch_version": {"$in": [current, "all"]}}` 필터링 강제.

### 2.1 임베딩 모델

- 한국어 + 영어 혼합 → `BAAI/bge-m3` (multilingual, dense + sparse 동시 지원, 1024-dim)
- 폴백: `intfloat/multilingual-e5-large`

### 2.2 검색 전략 — Hybrid

ChromaDB의 dense + 자체 BM25 wrapper:
- Dense (cosine) 가중 0.7
- BM25 가중 0.3
- 정렬 후 top-k 반환
- `where` 필터 적용 후 검색 (메타데이터 prefilter)

---

## 3. 데이터 수집 → chunk → upsert 파이프라인

```
fetch_raw()                # 출처별 원본 수집 (HTML/JSON/Markdown)
   ↓
normalize_to_jsonl()       # 인덱스별 표준 JSONL 스키마로 변환
   ↓
validate_against_schema()  # Pydantic 검증
   ↓
chunk()                    # playbook만 섹션 단위 split, 나머지는 1:1
   ↓
embed()                    # bge-m3 batch 인코딩
   ↓
upsert(ChromaDB)           # collection별 upsert (id = sha256(name+patch))
```

### 3.1 출처별 수집 책임

| 인덱스 | 수집 출처 | 비고 |
|---|---|---|
| units / traits / items / augments | Riot 공식 데이터 시트 (가능 시) / lolchess.gg 데이터 페이지 | 정적, 패치당 1회 |
| deck_templates | lolchess.gg meta tier list (사전 합의 도메인) | 패치당 1회. 새 패치 1주 후 갱신 |
| playbook | 팀이 작성한 마크다운 (수기) | 패치 무관, "all" |
| patch_summary | 공식 패치 노트 (Riot) | 패치 직후 24시간 이내 |
| glossary | 팀이 작성한 마크다운 (수기) | "all" |

### 3.2 정규화 JSONL 예시

`data/processed/units.jsonl`:
```json
{"id":"u_yasuo_14.9","name":"야스오","cost":3,"traits":["요원","검사"],
 "role":"DPS","image_url":"https://.../yasuo.png","patch_version":"14.9",
 "text":"야스오. 비용 3. 특성 요원 검사. 주력 딜러 ..."}
```

`text` 필드만 임베딩, 나머지는 ChromaDB metadata.

### 3.3 CLI

```bash
# 전체 인덱스 빌드
python -m backend.scripts.build_rag build --patch 14.9

# 특정 인덱스만 갱신
python -m backend.scripts.build_rag refresh --index patch_summary --patch 14.9

# 화이트리스트 export (디버깅용)
python -m backend.scripts.build_rag whitelist --patch 14.9 --out whitelist.json
```

---

## 4. 검색 API (Strategy Agent / Live Research가 호출)

```python
# backend/app/rag/search.py
from typing import Literal, Sequence
from pydantic import BaseModel

IndexName = Literal[
    "units", "traits", "items", "augments",
    "deck_templates", "playbook", "patch_summary", "glossary",
]

class RagChunk(BaseModel):
    id: str
    index: IndexName
    text: str
    metadata: dict
    score: float       # 0~1

class RagService:
    def search(
        self,
        index: IndexName,
        query: str,
        *,
        k: int = 5,
        patch_version: str,
        where: dict | None = None,
    ) -> list[RagChunk]: ...

    def multi_search(
        self,
        plan: list[tuple[IndexName, str, int]],   # [(index, query, k), ...]
        *,
        patch_version: str,
    ) -> list[RagChunk]: ...

    def get_whitelist(
        self,
        patch_version: str,
    ) -> dict[str, set[str]]:
        """{'units': {...}, 'items': {...}, 'traits': {...}, 'augments': {...}}"""
```

`multi_search`는 query plan을 한 번에 받아 병렬 실행.

`get_whitelist`는 Strategy Agent의 `verify_grounding`이 호출 — 결과를 캐시(LRU 16, TTL 1h).

### 4.1 검색 결과 정렬 / 중복 제거

- 동일 `id`는 한 번만 (deduplicate by `id`).
- score 내림차순.
- `score < 0.2`는 자동 제외.

---

## 5. patch_version 라이프사이클

```
[새 패치 공지]
    ↓
1. patch_summary 즉시 수집 (24h 이내)
    ↓
2. units/traits/items/augments 데이터 시트 수집 (24~48h)
    ↓
3. deck_templates는 1주 후 갱신 (메타 안정화 대기)
    ↓
4. PATCH_VERSION env 갱신 → 모든 검색이 새 patch로 자동 전환
```

이전 patch 데이터는 즉시 삭제하지 않고 7일간 보관 (롤백용).

```python
# backend/app/rag/lifecycle.py
def archive_patch(old_patch: str, archive_dir: Path): ...
def rollback_to_patch(target_patch: str): ...
```

---

## 6. Live Research 동적 chunk 승격

Live Research가 추출한 `WebFact`는 즉시 인덱싱하지 않는다(품질 위험). 대신:

```
[Live Research]
    ↓
WebFact (in-memory, request scope)
    ↓
[promotion_queue.jsonl] (7일 누적)
    ↓
[수동 검토 + 인덱싱] (옵션, MVP 미포함)
```

승격 큐 schema는 `04-agent-research-spec.md` §6 참조.

---

## 7. 결정성 / 재현성

| 측면 | 보장 |
|---|---|
| 동일 query + 동일 인덱스 state → 동일 결과 | ChromaDB는 deterministic. id 충돌 없음 (sha256). |
| 임베딩 재현성 | 모델 버전 + tokenizer pin (`requirements.txt`) |
| 검색 결과 정렬 | score 내림차순, tie-breaker는 `id` 사전순 |

**재현 테스트:**
```python
# tests/test_rag_repro.py
def test_same_query_same_results(rag_service):
    r1 = rag_service.search("units", "야스오", k=3, patch_version="14.9")
    r2 = rag_service.search("units", "야스오", k=3, patch_version="14.9")
    assert [c.id for c in r1] == [c.id for c in r2]
```

---

## 8. 스토리지 / 운영

- ChromaDB persistent path: `backend/data/chroma/`
- Volume size 추정: 8 인덱스 × 평균 100~500 chunk × 1024-dim float32 ≈ 50MB / 패치
- 서버 startup 시 collection count 검증. count=0 → fail-fast (건강 체크 `degraded`)

---

## 9. 인터페이스 — 다른 컴포넌트와의 계약

| 호출자 | 호출 함수 | 책임 |
|---|---|---|
| Strategy Agent `rag_retrieve` 노드 | `multi_search(plan, patch_version)` | query plan 실행 |
| Strategy Agent `verify_grounding` | `get_whitelist(patch_version)` | 화이트리스트 |
| Live Research `extract_facts` | `search("units"|"items"|..., query)` | 외부 fact의 ground truth 매칭 |
| Backend `/api/health` | `count_chunks()` | RAG 건강 체크 |
| Backend `/api/patch-info` | `current_patch_version()` | UI에 표시할 기준 패치 |

```python
# backend/app/rag/__init__.py
from .search import RagService, RagChunk

rag_service = RagService(
    chroma_path=settings.CHROMA_PATH,
    embedding_model=settings.EMBEDDING_MODEL,
)
```

---

## 10. 디렉토리 구조

```
backend/app/rag/
├── __init__.py
├── ingest/
│   ├── __init__.py
│   ├── fetch_riot_data.py
│   ├── fetch_lolchess.py
│   ├── parse_patch_notes.py
│   └── normalize.py
├── chunk.py
├── embed.py
├── index.py                 # ChromaDB wrapper (collections)
├── search.py                # RagService
├── whitelist.py             # get_whitelist + cache
├── lifecycle.py             # patch archive/rollback
└── schemas.py               # JSONL row schemas (Pydantic)

backend/scripts/
└── build_rag.py             # CLI

backend/data/
├── raw/                     # 크롤링 원본 (gitignore)
├── processed/               # 정규화 JSONL (인덱스별)
└── chroma/                  # ChromaDB persistent (gitignore)
```

---

## 11. 평가

`evals/rag_eval.jsonl` 30 query: query → expected top-3 chunk id (수기 작성).

| 지표 | 목표 |
|---|---|
| Recall@3 | ≥ 0.85 |
| MRR (Mean Reciprocal Rank) | ≥ 0.7 |
| Whitelist 정확성 (unit name이 모두 ko 정자체) | 100% |
| patch filter 정확성 (검색 결과의 patch_version 일치) | 100% |

CI에서 매 PR.

---

## 12. 기획서 피드백

| # | 기획서 | 문제 | 본 spec |
|---|---|---|---|
| 1 | "RAG에 기물/특성/아이템/증강체/덱 템플릿 저장"(§4.1.3) | chunking 단위, 메타데이터, 임베딩 모델 미정 | §2 표에 8개 인덱스 + 메타데이터 + 모델 명시 |
| 2 | "최근 패치의 주요 변경점 정리"(§4.1.3) | patch_version 메타데이터 없으면 옛 정보 섞임 | §2 1급 메타 + 검색 시 필수 필터 |
| 3 | "벡터 DB 저장"(§5.3.3) | 단일 collection? 인덱스별 분리? 미정 | §2에 ChromaDB collection 8개 분리 |
| 4 | 검색 품질 평가 부재 | "검색되는지 확인" 한 줄 | §11 Recall@3, MRR 정량 |
| 5 | 새 패치 갱신 절차 미정 | 운영 시점에 혼란 | §5 라이프사이클 정의 |
| 6 | 한국어 임베딩 모델 미언급 | 품질 영향 큼 | §2.1 bge-m3 채택 + 폴백 |
| 7 | "용어 사전"(§4.1.3 마지막) | 어디에 어떻게 쓰이는지 모호 | §2 `glossary` 인덱스 + Strategy `recommend` 노드의 LLM 프롬프트 컨텍스트로 활용 |
