from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "services" / "rag" / "src"
sys.path.insert(0, str(SRC_ROOT))

from deckguru_rag.search import ChromaPatchSummarySearch  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python services/rag/scripts/search_chroma.py [index] [--patch PATCH] <query>")

    index = "patch_summary"
    patch_version = None
    args = sys.argv[1:]
    if args[0] in {"patch_summary", "deck_templates"}:
        index = args.pop(0)
    if len(args) >= 2 and args[0] == "--patch":
        patch_version = args[1]
        args = args[2:]
    query = " ".join(args)
    service = ChromaPatchSummarySearch(
        data_dir=REPO_ROOT / "data" / "rag" / "processed" / "patch_summary",
        persist_dir=REPO_ROOT / "data" / "rag" / "vectorstore" / "chroma",
    )
    for result in service.search(query, index=index, k=5, patch_version=patch_version):
        title = result.get("target_name") or result.get("name")
        print(f"[{result['score']}] {result['index']} {title}")
        print(result["text"])
        print(result["source_url"])
        print()


if __name__ == "__main__":
    main()
