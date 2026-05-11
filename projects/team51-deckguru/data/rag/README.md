# DeckGuru RAG Data

RAG 인덱스에 넣기 전후의 데이터 산출물을 보관하는 영역입니다.

## Layout

```text
data/rag/
  raw/
    patch_notes/
    lolchess/
    metatft/
    tactics_tools/
  processed/
    units/
    traits/
    items/
    augments/
    deck_templates/
    playbook/
    patch_summary/
    glossary/
  seeds/
  vectorstore/
```

- `raw`: 원천 수집 데이터
- `processed`: schema 검증이 끝난 JSONL/chunk 데이터
- `seeds`: 직접 작성하는 glossary/playbook 같은 초기 데이터
- `vectorstore`: 로컬 개발용 vector DB 파일 또는 export 산출물

## Data Policy

- `raw`와 `processed` 데이터는 팀원이 같은 입력으로 Chroma를 재빌드할 수 있도록 커밋합니다.
- `vectorstore/chroma/`는 로컬 빌드 산출물이므로 커밋하지 않습니다.
- 새 패치가 나오면 raw를 다시 수집하고 processed JSONL/current manifest를 갱신한 뒤 Chroma를 재빌드합니다.
- 아직 구현되지 않은 인덱스 폴더는 RAG spec의 최종 구조를 미리 맞춰 둔 자리입니다.

## Current Indexes

현재 실제 데이터가 들어간 인덱스는 아래 두 개입니다.

| Index | Current patch | Source | Files |
| --- | --- | --- | --- |
| `patch_summary` | `17.2` | Riot official patch notes | `processed/patch_summary/17.2.jsonl` |
| `deck_templates` | `17.2b` | Lolchess meta/decks | `processed/deck_templates/17.2b.jsonl` |

## Patch Summary

`processed/patch_summary`는 패치노트 RAG 인덱스의 입력 데이터입니다. 패치노트 요약은 Riot 공식 패치노트를 기준 source로 사용합니다.

```text
processed/patch_summary/
  current_patch.json
  17.2.jsonl
```

JSONL 한 줄은 하나의 검색 chunk이며 `patch_version`, `source`, `section`, `target_kind`, `target_name`, `change_type`, `text`를 포함합니다. 현재 `source`는 `riot`만 사용합니다.

Raw input:

```text
raw/patch_notes/
  riot_latest_patch_note.json
```

## Deck Templates

`processed/deck_templates`는 추천 메타와 덱 통계 RAG 인덱스의 입력 데이터입니다.

```text
raw/lolchess/
  lolchess_meta.json
  lolchess_decks.json
processed/deck_templates/
  current_patch.json
  17.2b.jsonl
```

JSONL 한 줄은 하나의 덱 chunk이며 `patch_version`, `source`, `name`, `core_units`, `key_items`, `traits`, `win_rate`, `top4_rate`, `play_rate`, `text`를 포함합니다.

- `source=decks`: Lolchess 덱 통계. 현재 raw 기준 `patch_version=17.2`
- `source=meta`: Lolchess 추천 메타. `guides[].name`에서 `v17.2b`를 파싱해 `patch_version=17.2b`로 저장

검색에서는 `17.2`처럼 suffix 없는 patch를 요청하면 `17.2`, `17.2b` 같은 같은 패치 패밀리를 함께 조회할 수 있습니다.

## Rebuild

Chroma vectorstore는 repo에 포함하지 않습니다. 각자 아래 명령으로 재생성합니다.

```bash
services/rag/.venv/Scripts/python.exe services/rag/scripts/build_chroma.py
```

생성 위치:

```text
vectorstore/chroma/
```
