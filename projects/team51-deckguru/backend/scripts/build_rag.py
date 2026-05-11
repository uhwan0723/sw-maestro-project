"""Build and refresh Chroma RAG indices from processed JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rag.chroma_service import BGEM3Embedding, WHITELIST_INDICES, resolve_chroma_path  # noqa: E402
from app.rag.filters import patch_family_versions, patch_where  # noqa: E402
from app.rag.service import RagUnavailableError  # noqa: E402
from app.settings import settings  # noqa: E402

SUPPORTED_BUILD_INDICES = ("patch_summary", "deck_templates")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Rebuild supported RAG collections")
    build_parser.add_argument("--patch", default=settings.patch_version)

    refresh_parser = subparsers.add_parser("refresh", help="Refresh one RAG collection")
    refresh_parser.add_argument("--index", choices=SUPPORTED_BUILD_INDICES, required=True)
    refresh_parser.add_argument("--patch", default=settings.patch_version)

    whitelist_parser = subparsers.add_parser("whitelist", help="Export whitelist names")
    whitelist_parser.add_argument("--patch", default=settings.patch_version)
    whitelist_parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            counts = build(args.patch)
            print(json.dumps(counts, ensure_ascii=False, indent=2))
            return 0
        if args.command == "refresh":
            count = refresh(args.index, args.patch)
            print(json.dumps({args.index: count}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "whitelist":
            whitelist = export_whitelist(args.patch)
            args.out.write_text(
                json.dumps(
                    {key: sorted(values) for key, values in whitelist.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if all(len(values) == 0 for values in whitelist.values()):
                print("warning: whitelist collections are empty", file=sys.stderr)
            return 0
    except (FileNotFoundError, RagUnavailableError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 1


def build(patch: str) -> dict[str, int]:
    client = _create_client()
    embedder = BGEM3Embedding(settings.embedding_model)
    counts: dict[str, int] = {}
    for index in SUPPORTED_BUILD_INDICES:
        paths = _jsonl_paths_for_patch(index, patch)
        records = _load_records(paths)
        _recreate_collection(client, index)
        if records:
            _upsert_records(client.get_collection(name=index), embedder, index, records)
        _write_manifest(index, patch, paths, records)
        counts[index] = len(records)
    return counts


def refresh(index: str, patch: str) -> int:
    client = _create_client()
    embedder = BGEM3Embedding(settings.embedding_model)
    paths = _jsonl_paths_for_patch(index, patch)
    records = _load_records(paths)
    collection = client.get_or_create_collection(name=index)
    try:
        collection.delete(where=patch_where(patch))
    except Exception:
        pass
    if records:
        _upsert_records(collection, embedder, index, records)
    _write_manifest(index, patch, paths, records)
    return len(records)


def export_whitelist(patch: str) -> dict[str, set[str]]:
    del patch
    whitelist: dict[str, set[str]] = {}
    for index in WHITELIST_INDICES:
        names: set[str] = set()
        index_dir = _processed_dir() / index
        for path in sorted(index_dir.glob("*.jsonl")):
            for record in _load_records([path]):
                name = record.get("name") or record.get("target_name")
                if isinstance(name, str) and name:
                    names.add(name)
        whitelist[index] = names
    return whitelist


def _create_client() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RagUnavailableError(
            "chromadb is not installed. Install backend RAG dependencies with "
            '`pip install -e ".[backend,dev,rag]"`.'
        ) from exc
    persist_path = resolve_chroma_path(settings.chroma_path)
    persist_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_path))


def _processed_dir() -> Path:
    return REPO_ROOT / "data" / "rag" / "processed"


def _jsonl_paths_for_patch(index: str, patch: str) -> list[Path]:
    index_dir = _processed_dir() / index
    family = set(patch_family_versions(patch))
    paths = [
        path
        for path in sorted(index_dir.glob("*.jsonl"))
        if path.stem in family and path.stem != "all"
    ]
    if not paths:
        raise FileNotFoundError(f"no processed JSONL found for index={index} patch={patch}")
    return paths


def _load_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def _recreate_collection(client: Any, index: str) -> None:
    try:
        client.delete_collection(name=index)
    except Exception:
        pass
    client.create_collection(name=index)


def _upsert_records(collection: Any, embedder: BGEM3Embedding, index: str, records: list[dict[str, Any]]) -> None:
    documents = [str(record["text"]) for record in records]
    collection.upsert(
        ids=[str(record["id"]) for record in records],
        documents=documents,
        metadatas=[_metadata(record, index) for record in records],
        embeddings=embedder.embed_many(documents),
    )


def _metadata(record: dict[str, Any], index: str) -> dict[str, str | int | float | bool]:
    raw: dict[str, Any] = {"index": index}
    for key, value in record.items():
        if key in {"id", "text", "metadata"}:
            continue
        raw[key] = value
    nested = record.get("metadata")
    if isinstance(nested, dict):
        for key, value in nested.items():
            raw.setdefault(key, value)
    return {key: _metadata_value(value) for key, value in raw.items()}


def _metadata_value(value: Any) -> str | int | float | bool:
    if isinstance(value, (str, int, float, bool)):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


def _write_manifest(
    index: str,
    requested_patch: str,
    paths: list[Path],
    records: list[dict[str, Any]],
) -> None:
    index_dir = _processed_dir() / index
    timestamps = [
        str(record.get("fetched_at") or record.get("last_updated"))
        for record in records
        if record.get("fetched_at") or record.get("last_updated")
    ]
    updated_at = max(timestamps) if timestamps else datetime.now(timezone.utc).isoformat()
    sources = sorted({str(record.get("source")) for record in records if record.get("source")})
    source_urls = sorted({str(record.get("source_url")) for record in records if record.get("source_url")})
    current_patch = paths[0].stem if len(paths) == 1 else requested_patch
    jsonl_path: str | list[str] = paths[0].name if len(paths) == 1 else [path.name for path in paths]

    manifest = {
        "current_patch": current_patch,
        "index": index,
        "last_updated": updated_at,
        "fetched_at": updated_at,
        "record_count": len(records),
        "sources": sources,
        "source_urls": source_urls,
        "jsonl_path": jsonl_path,
    }
    (index_dir / "current_patch.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
