"""guide_node — case_type 기준 단계 리스트 룩업 (data/guides.yaml)."""
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import settings
from app.state import LegalState


@lru_cache(maxsize=1)
def _load_guides() -> dict[str, list[str]]:
    path = Path(settings.guides_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def guide_node(state: LegalState) -> dict:
    case_type = state.get("case_type")
    if not case_type:
        return {"guide_steps": None}

    guides = _load_guides()
    steps = guides.get(case_type)
    return {"guide_steps": steps if steps else None}
