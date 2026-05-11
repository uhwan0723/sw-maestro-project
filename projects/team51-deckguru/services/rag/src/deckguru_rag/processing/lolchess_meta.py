import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DeckTemplateRecord:
    id: str
    index: str
    patch_version: str
    source: str
    source_url: str
    fetched_at: str
    name: str
    core_units: list[str]
    key_items: list[str]
    traits: list[str]
    average_place: float | None
    win_rate: float | None
    top4_rate: float | None
    play_rate: float | None
    games: int | None
    text: str
    metadata: dict[str, Any]


def build_lolchess_meta_jsonl(raw_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[DeckTemplateRecord] = []

    for raw_path in sorted(raw_dir.glob("lolchess_*.json")):
        document = json.loads(raw_path.read_text(encoding="utf-8"))
        records.extend(_records_from_document(document))

    records = _dedupe_records(records)
    patch_version = _select_patch_version(records)
    output_path = output_dir / f"{patch_version}.jsonl"
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    _write_manifest(output_dir, patch_version, records)
    return output_path


def _records_from_document(document: dict[str, Any]) -> list[DeckTemplateRecord]:
    source = str(document["source"])
    source_url = str(document["url"])
    fetched_at = str(document["fetched_at"])
    queries = _queries(document["next_data"])
    refs = _collect_refs(queries)
    records: list[DeckTemplateRecord] = []

    for query in queries:
        query_key = query.get("queryKey", [])
        data = query.get("state", {}).get("data")
        if not isinstance(data, dict):
            continue

        if source == "meta" and query_key[:1] == ["getGuideDecks"]:
            records.extend(_guide_deck_records(data, refs, source, source_url, fetched_at))
        elif source == "decks" and query_key[:1] == ["meta-decks"]:
            records.extend(_meta_deck_records(data, refs, source, source_url, fetched_at))

    return records


def _guide_deck_records(
    data: dict[str, Any],
    refs: dict[str, dict[str, str]],
    source: str,
    source_url: str,
    fetched_at: str,
) -> list[DeckTemplateRecord]:
    patch_version = _patch_from_guides(data.get("guides", []))
    if patch_version == "unknown":
        patch_version = _infer_patch_version(data)
    guide_decks = data.get("guideDecks") or data.get("guides") or []
    return [
        _record_from_guide_deck(deck, refs, source, source_url, fetched_at, patch_version)
        for deck in _iter_dicts(guide_decks)
    ]


def _meta_deck_records(
    data: dict[str, Any],
    refs: dict[str, dict[str, str]],
    source: str,
    source_url: str,
    fetched_at: str,
) -> list[DeckTemplateRecord]:
    patch_version = _infer_patch_version(data)
    if patch_version == "unknown":
        patch_version = _patch_from_revisions(data.get("patchRevisions", []))
    meta_decks = data.get("metaDeckList") or []
    return [
        _record_from_meta_deck(deck, refs, source, source_url, fetched_at, patch_version)
        for deck in _iter_dicts(meta_decks)
    ]


def _record_from_guide_deck(
    deck: dict[str, Any],
    refs: dict[str, dict[str, str]],
    source: str,
    source_url: str,
    fetched_at: str,
    patch_version: str,
) -> DeckTemplateRecord:
    name = _first_string(deck, ["name", "title", "deckName", "guideTitle"]) or "unknown"
    slots = deck.get("data", {}).get("slots", []) if isinstance(deck.get("data"), dict) else []
    core_units = [
        _resolve_ref(refs["champions"], slot.get("champion"))
        for slot in slots
        if isinstance(slot, dict) and slot.get("champion")
    ]
    key_items = [
        _resolve_ref(refs["items"], item)
        for slot in slots
        if isinstance(slot, dict)
        for item in slot.get("items", [])
    ]
    traits = [
        _resolve_ref(refs["traits"], trait)
        for trait in deck.get("data", {}).get("traits", [])
    ] if isinstance(deck.get("data"), dict) else []
    return _make_record(
        deck=deck,
        source=source,
        source_url=source_url,
        fetched_at=fetched_at,
        patch_version=patch_version,
        name=name,
        core_units=_dedupe_strings(core_units),
        key_items=_dedupe_strings(key_items),
        traits=_dedupe_strings(traits),
    )


def _record_from_meta_deck(
    deck: dict[str, Any],
    refs: dict[str, dict[str, str]],
    source: str,
    source_url: str,
    fetched_at: str,
    patch_version: str,
) -> DeckTemplateRecord:
    deck_body = deck.get("deck", {}) if isinstance(deck.get("deck"), dict) else {}
    champions = deck_body.get("champions", [])
    name = _deck_name_from_champions(champions, refs) or _first_string(deck, ["name", "title"]) or "unknown"
    core_units = [
        _resolve_ref(refs["champions"], champion.get("key"))
        for champion in champions
        if isinstance(champion, dict) and champion.get("key")
    ]
    key_items = [
        _resolve_ref(refs["items"], item)
        for champion in champions
        if isinstance(champion, dict)
        for item in champion.get("items", [])
    ]
    traits = [
        _resolve_ref(refs["traits"], trait.get("key"))
        for trait in deck_body.get("traits", [])
        if isinstance(trait, dict) and trait.get("key")
    ]
    return _make_record(
        deck=deck,
        source=source,
        source_url=source_url,
        fetched_at=fetched_at,
        patch_version=patch_version,
        name=name,
        core_units=_dedupe_strings(core_units),
        key_items=_dedupe_strings(key_items),
        traits=_dedupe_strings(traits),
    )


def _make_record(
    *,
    deck: dict[str, Any],
    source: str,
    source_url: str,
    fetched_at: str,
    patch_version: str,
    name: str,
    core_units: list[str],
    key_items: list[str],
    traits: list[str],
) -> DeckTemplateRecord:
    average_place = _first_float(deck, ["avgPlacement", "averagePlace", "avgPlace", "placement"])
    win_rate = _first_float(deck, ["winRate", "win_rate"])
    top4_rate = _first_float(deck, ["top4Rate", "topRate", "top4_rate"])
    play_rate = _first_float(deck, ["pickRate", "playRate", "usageRate"])
    games = _first_int(deck, ["games", "count", "playCount", "totalGames"])
    text = _build_text(name, core_units, key_items, traits, average_place, win_rate, top4_rate, games)
    record_id = _record_id(source, patch_version, name, text)
    return DeckTemplateRecord(
        id=record_id,
        index="deck_templates",
        patch_version=patch_version,
        source=source,
        source_url=source_url,
        fetched_at=fetched_at,
        name=name,
        core_units=core_units,
        key_items=key_items,
        traits=traits,
        average_place=average_place,
        win_rate=win_rate,
        top4_rate=top4_rate,
        play_rate=play_rate,
        games=games,
        text=text,
        metadata={"raw_source": source, "deck_key": str(deck.get("key") or deck.get("deckKey") or "")},
    )


def _queries(next_data: dict[str, Any]) -> list[dict[str, Any]]:
    page_props = next_data.get("props", {}).get("pageProps", {})
    return page_props.get("dehydratedState", {}).get("queries", [])


def _collect_refs(queries: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    refs = {"champions": {}, "items": {}, "traits": {}}
    for query in queries:
        data = query.get("state", {}).get("data")
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("refs"), dict):
            _merge_refs(refs, data["refs"])
        for key, target in (
            ("champions", "champions"),
            ("items", "items"),
            ("traits", "traits"),
        ):
            if isinstance(data.get(key), list):
                _merge_ref_list(refs[target], data[key])
    return refs


def _merge_refs(refs: dict[str, dict[str, str]], raw_refs: dict[str, Any]) -> None:
    for key in ("champions", "items", "traits"):
        if isinstance(raw_refs.get(key), list):
            _merge_ref_list(refs[key], raw_refs[key])


def _merge_ref_list(target: dict[str, str], values: list[Any]) -> None:
    for value in values:
        if not isinstance(value, dict):
            continue
        name = value.get("name")
        if not isinstance(name, str):
            continue
        for key in ("key", "ingameKey", "apiName", "characterName"):
            ref_key = value.get(key)
            if isinstance(ref_key, str):
                target[ref_key] = name
                target[ref_key.replace("TFT17_", "")] = name


def _resolve_ref(refs: dict[str, str], key: Any) -> str:
    if not isinstance(key, str):
        return ""
    return refs.get(key) or refs.get(key.replace("TFT17_", "")) or key


def _deck_name_from_champions(champions: Any, refs: dict[str, dict[str, str]]) -> str | None:
    if not isinstance(champions, list):
        return None
    core = [
        champion
        for champion in champions
        if isinstance(champion, dict) and isinstance(champion.get("coreRank"), int)
    ]
    core.sort(key=lambda champion: champion["coreRank"])
    if not core:
        return None
    return " ".join(_resolve_ref(refs["champions"], champion.get("key")) for champion in core[:2])


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if any(key in value for key in ("name", "deck", "data")):
            yield value
            return
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _extract_names(deck: dict[str, Any], keys: list[str]) -> list[str]:
    names: list[str] = []
    for key in keys:
        if key in deck:
            names.extend(_names_from_value(deck[key]))
    return _dedupe_strings(names)


def _names_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("name", "displayName", "characterName", "apiName", "key"):
            if isinstance(value.get(key), str):
                return [value[key]]
        names: list[str] = []
        for child in value.values():
            names.extend(_names_from_value(child))
        return names
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_names_from_value(item))
        return names
    return []


def _first_string(deck: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = deck.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_float(deck: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = deck.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _first_int(deck: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        value = deck.get(key)
        if isinstance(value, int):
            return value
    return None


def _build_text(
    name: str,
    core_units: list[str],
    key_items: list[str],
    traits: list[str],
    average_place: float | None,
    win_rate: float | None,
    top4_rate: float | None,
    games: int | None,
) -> str:
    parts = [f"덱: {name}"]
    if traits:
        parts.append(f"시너지: {', '.join(traits[:8])}")
    if core_units:
        parts.append(f"핵심 유닛: {', '.join(core_units[:12])}")
    if key_items:
        parts.append(f"핵심 아이템: {', '.join(key_items[:12])}")
    stats = []
    if average_place is not None:
        stats.append(f"평균 등수 {average_place}")
    if win_rate is not None:
        stats.append(f"승률 {win_rate}")
    if top4_rate is not None:
        stats.append(f"TOP4 {top4_rate}")
    if games is not None:
        stats.append(f"게임 수 {games}")
    if stats:
        parts.append("통계: " + ", ".join(stats))
    return " | ".join(parts)


def _infer_patch_version(data: dict[str, Any]) -> str:
    text = json.dumps(data, ensure_ascii=False)
    matches = re.findall(r"\bv?(\d{2}\.\d+[a-z]?)\b", text, flags=re.IGNORECASE)
    return matches[0].lower() if matches else "unknown"


def _patch_from_guides(guides: Any) -> str:
    if not isinstance(guides, list):
        return "unknown"
    for guide in guides:
        if not isinstance(guide, dict):
            continue
        name = guide.get("name")
        if not isinstance(name, str):
            continue
        match = re.search(r"\bv?(\d{2}\.\d+[a-z]?)\b", name, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return "unknown"


def _patch_from_revisions(revisions: Any) -> str:
    if isinstance(revisions, list) and revisions:
        value = revisions[0].get("patchVersion") if isinstance(revisions[0], dict) else None
        if isinstance(value, str):
            return value.lower()
    return "unknown"


def _record_id(source: str, patch_version: str, name: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}|{patch_version}|{name}|{text}".encode()).hexdigest()
    return f"deck_template_{digest[:16]}"


def _dedupe_records(records: list[DeckTemplateRecord]) -> list[DeckTemplateRecord]:
    seen: set[str] = set()
    deduped: list[DeckTemplateRecord] = []
    for record in records:
        key = f"{record.source}|{record.name}|{record.text}"
        if key in seen or record.name == "unknown":
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _select_patch_version(records: list[DeckTemplateRecord]) -> str:
    versions = [record.patch_version for record in records if record.patch_version != "unknown"]
    if not versions:
        return "unknown"
    return max(versions, key=_patch_sort_key)


def _patch_sort_key(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)([a-z]?)$", version, flags=re.IGNORECASE)
    if not match:
        return (0, 0, 0)
    suffix = match.group(3).lower()
    suffix_rank = 0 if not suffix else ord(suffix) - ord("a") + 1
    return (int(match.group(1)), int(match.group(2)), suffix_rank)


def _write_manifest(output_dir: Path, patch_version: str, records: list[DeckTemplateRecord]) -> None:
    manifest = {
        "current_patch": patch_version,
        "index": "deck_templates",
        "record_count": len(records),
        "sources": sorted({record.source for record in records}),
        "jsonl_path": f"{patch_version}.jsonl",
    }
    (output_dir / "current_patch.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
