# DeckGuru RAG Service

RAG 담당 영역입니다. Backend/Strategy Agent가 호출하는 검색 계층과 인덱싱 파이프라인 코드를 이곳에서 관리합니다.

## Responsibilities

- 8개 RAG 인덱스 구성: `units`, `traits`, `items`, `augments`, `deck_templates`, `playbook`, `patch_summary`, `glossary`
- raw 데이터를 검색 가능한 chunk로 정규화
- embedding 생성 및 vector DB upsert
- `patch_version` 기반 검색 필터링
- `search`, `multi_search`, `get_whitelist` 인터페이스 제공

## Layout

```text
services/rag/
  requirements.txt
  scripts/
    build_chroma.py
    build_deck_templates.py
    fetch_lolchess_meta.py
    search_chroma.py
  src/deckguru_rag/
    embeddings/
    ingestion/
    processing/
    search/
    storage/
```

Canonical spec: `../../docs/specs/03-agent-rag-spec.md`, `../../docs/specs/07-data-contracts.md`

## ChromaDB

RAG 전용 의존성만 설치합니다. 루트 프로젝트 의존성은 변경하지 않습니다.

```bash
python -m venv services/rag/.venv
services/rag/.venv/Scripts/python.exe -m pip install -r services/rag/requirements.txt
```

현재 embedding 모델은 `BAAI/bge-m3`입니다. BGE-M3는 1024차원 dense embedding을 생성하며 한국어를 포함한 다국어 검색에 사용할 수 있습니다. 첫 실행 시 Hugging Face 모델 파일을 내려받기 때문에 시간이 걸릴 수 있습니다.

```bash
services/rag/.venv/Scripts/python.exe services/rag/scripts/build_chroma.py
services/rag/.venv/Scripts/python.exe services/rag/scripts/search_chroma.py "쓰레쉬 너프"
services/rag/.venv/Scripts/python.exe services/rag/scripts/search_chroma.py deck_templates "마스터 이 덱"
```

Chroma persistent DB는 아래 경로에 생성됩니다. 이 경로는 git에 커밋하지 않습니다.

```text
data/rag/vectorstore/chroma/
```

## Current Data

현재 Chroma 빌드는 아래 두 collection을 생성합니다.

- `patch_summary`: 패치노트 변경 요약
- `deck_templates`: Lolchess 추천 메타와 덱 통계

## Backend Usage

Backend에서 사용하려면 먼저 RAG 의존성을 설치하고 Chroma vectorstore를 빌드해야 합니다.

```bash
python -m venv services/rag/.venv
services/rag/.venv/Scripts/python.exe -m pip install -r services/rag/requirements.txt
services/rag/.venv/Scripts/python.exe services/rag/scripts/build_chroma.py
```

Backend 런타임에서 `deckguru_rag`를 import할 수 있게 `services/rag/src`를 Python path에 추가합니다. 개발 중에는 아래처럼 `sys.path`에 추가해서 바로 확인할 수 있습니다.

```python
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "rag" / "src"))

from deckguru_rag.search import ChromaPatchSummarySearch

rag_search = ChromaPatchSummarySearch(
    data_dir=REPO_ROOT / "data" / "rag" / "processed" / "patch_summary",
    persist_dir=REPO_ROOT / "data" / "rag" / "vectorstore" / "chroma",
)
```

패치노트 검색:

```python
results = rag_search.search(
    "쓰레쉬 너프",
    index="patch_summary",
    patch_version="17.2",
    k=5,
)
```

추천 메타/덱 검색:

```python
results = rag_search.search(
    "마스터 이 덱",
    index="deck_templates",
    patch_version="17.2",
    k=5,
)
```

`patch_version`은 패치 패밀리 검색을 지원합니다. 예를 들어 `17.2`를 넘기면 `17.2`, `17.2b`, `17.2c`처럼 같은 minor patch 계열을 함께 검색합니다. `17.2b`처럼 suffix까지 넘기면 해당 버전만 검색합니다.

검색 결과는 list of dict 형태입니다.

```python
[
    {
        "id": "deck_template_...",
        "index": "deck_templates",
        "score": 1.0323,
        "text": "덱: 마스터 이 킨드레드 | ...",
        "source_url": "https://lolchess.gg/decks?hl=ko",
        "patch_version": "17.2",
        "name": "마스터 이 킨드레드",
    }
]
```

주의할 점:

- `data/rag/vectorstore/chroma/`는 로컬 빌드 산출물이며 git에 커밋하지 않습니다.
- raw/processed JSON은 커밋해도 되지만, Chroma DB는 각자 `build_chroma.py`로 다시 생성합니다.
- 첫 실행 시 `BAAI/bge-m3` 모델 다운로드 때문에 시간이 걸릴 수 있습니다.

## Lolchess Meta

추천 메타와 덱 통계는 Lolchess의 Next.js page data에서 수집합니다.

```bash
services/rag/.venv/Scripts/python.exe services/rag/scripts/fetch_lolchess_meta.py
services/rag/.venv/Scripts/python.exe services/rag/scripts/build_deck_templates.py
services/rag/.venv/Scripts/python.exe services/rag/scripts/build_chroma.py
```

Raw data:

```text
data/rag/raw/lolchess/lolchess_meta.json
data/rag/raw/lolchess/lolchess_decks.json
```

Processed data:

```text
data/rag/processed/deck_templates/{patch_version}.jsonl
data/rag/processed/deck_templates/current_patch.json
```
