from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "services" / "rag" / "src"
sys.path.insert(0, str(SRC_ROOT))

from deckguru_rag.ingestion import fetch_lolchess_meta_pages  # noqa: E402


def main() -> None:
    output_dir = REPO_ROOT / "data" / "rag" / "raw" / "lolchess"
    for path in fetch_lolchess_meta_pages(output_dir):
        print(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
