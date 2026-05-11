"""classify_node — 사용자 질문을 case_type 으로 분류.

Solar mini + JSON 모드 + few-shot. 실패 시 키워드 폴백.
"""
import json
import logging

from app.llm.solar_client import SolarAPIError, call_flash_json
from app.state import LegalState
from app.utils.keyword_fallback import ClassificationOutput, classify_by_keyword
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

_FEW_SHOT_HEADER = "다음은 분류 예시입니다:\n\n"


def _build_few_shot_block(examples_json: str) -> str:
    examples = json.loads(examples_json)
    lines = []
    for ex in examples:
        lines.append(f"질문: {ex['input']}")
        exp = ex["expected"]
        lines.append(
            f"→ case_type={exp['case_type']}, needs_settlement={str(exp['needs_settlement']).lower()}, confidence={exp['confidence']}"
        )
        lines.append("")
    return _FEW_SHOT_HEADER + "\n".join(lines)


def _build_user_prompt(state: LegalState, few_shot_block: str) -> str:
    history = state.get("history", [])
    recent = history[-4:] if len(history) > 4 else history
    history_text = ""
    if recent:
        history_text = "\n이전 대화:\n" + "\n".join(
            f"[{m['role']}] {m['content']}" for m in recent
        )

    return f"{few_shot_block}\n현재 질문을 분류하세요:{history_text}\n\n질문: {state['user_query']}"


async def classify_node(state: LegalState) -> dict:
    """반환: {domain, case_type, needs_settlement, classification_confidence}."""
    system_prompt = load_prompt("classify_system.txt")
    examples_json = load_prompt("classify_examples.json")
    few_shot_block = _build_few_shot_block(examples_json)
    user_prompt = _build_user_prompt(state, few_shot_block)

    try:
        result: ClassificationOutput = await call_flash_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ClassificationOutput,
        )
    except SolarAPIError as exc:
        logger.warning("Solar API 실패, 키워드 폴백 사용: %s", exc)
        result = classify_by_keyword(state["user_query"])

    needs_settlement = result.needs_settlement
    if result.case_type in ("OUT_OF_SCOPE", "RECKLESS_DRIVING"):
        needs_settlement = False

    return {
        "domain": "교통",
        "case_type": result.case_type,
        "needs_settlement": needs_settlement,
        "classification_confidence": result.confidence,
    }
