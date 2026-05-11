from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "services" / "rag" / "src"
sys.path.insert(0, str(SRC_ROOT))

from deckguru_rag.storage import build_chroma_indices  # noqa: E402


def main() -> None:
    data_dir = REPO_ROOT / "data" / "rag" / "processed" / "patch_summary"
    persist_dir = REPO_ROOT / "data" / "rag" / "vectorstore" / "chroma"
    counts = build_chroma_indices(data_dir=data_dir, persist_dir=persist_dir)
    for index, count in counts.items():
        print(f"{index}: upserted={count}")
    print(persist_dir.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
