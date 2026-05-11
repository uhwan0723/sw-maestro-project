"""평가셋 10개를 실제 Solar API 로 돌려 정확도 csv 출력.

RPM 초과 방지를 위해 호출 사이에 7초 딜레이.
Upstage 플랜에 따라 CALL_DELAY 와 MAX_EVAL 조정.
"""
import asyncio
import csv
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logging.basicConfig(level=logging.WARNING)

from app.agents.classify import classify_node

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "scenarios.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "eval_results.csv")

MAX_EVAL = 10
CALL_DELAY = 7.0


def _confidence_range(conf: float) -> str:
    if conf >= 0.9:
        return "0.9~1.0"
    if conf >= 0.7:
        return "0.7~0.9"
    if conf >= 0.5:
        return "0.5~0.7"
    if conf >= 0.4:
        return "0.4~0.5"
    return "<0.4"


async def run_eval() -> None:
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        all_scenarios = json.load(f)

    scenarios = all_scenarios[:MAX_EVAL]
    print(f"평가 시작: {len(scenarios)}개 시나리오 (호출 간격 {CALL_DELAY}초)\n")

    rows = []
    correct = 0

    for i, sc in enumerate(scenarios):
        query = sc["input"]
        expected_ct = sc["expected"]["case_type"]
        expected_conf = sc["expected"]["confidence"]

        if i > 0:
            print(f"  대기 중 ({CALL_DELAY}초)...")
            await asyncio.sleep(CALL_DELAY)

        state = {
            "session_id": "eval",
            "user_query": query,
            "history": [],
            "retrieved_docs": [],
        }

        result = await classify_node(state)
        actual_ct = result["case_type"]
        actual_conf = result["classification_confidence"]
        match = actual_ct == expected_ct
        if match:
            correct += 1

        rows.append({
            "input": query,
            "expected_case_type": expected_ct,
            "actual_case_type": actual_ct,
            "match": "O" if match else "X",
            "expected_confidence_range": _confidence_range(expected_conf),
            "actual_confidence": f"{actual_conf:.2f}",
        })

        print(f"[{i+1:02d}] {'O' if match else 'X'} expected={expected_ct} actual={actual_ct} conf={actual_conf:.2f}")
        print(f"     질문: {query}")

    accuracy = correct / len(scenarios)
    print(f"\n정확도: {correct}/{len(scenarios)} = {accuracy:.1%}")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"결과 저장: {OUTPUT_PATH}")
    if accuracy < 0.80:
        print("⚠️  정확도 80% 미달")
        sys.exit(1)
    else:
        print("✓ 정확도 80% 이상 통과")


if __name__ == "__main__":
    asyncio.run(run_eval())
