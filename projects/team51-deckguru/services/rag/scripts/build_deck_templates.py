from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "services" / "rag" / "src"
sys.path.insert(0, str(SRC_ROOT))

from deckguru_rag.processing import build_lolchess_meta_jsonl  # noqa: E402


def main() -> None:
    raw_dir = REPO_ROOT / "data" / "rag" / "raw" / "lolchess"
    output_dir = REPO_ROOT / "data" / "rag" / "processed" / "deck_templates"
    output_path = build_lolchess_meta_jsonl(raw_dir, output_dir)
    print(output_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
