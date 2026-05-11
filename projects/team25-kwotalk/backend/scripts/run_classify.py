"""CLI 로 classify_node 단독 실행."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.agents.classify import classify_node
from app.constants import CLARIFY_THRESHOLD


async def main(query: str) -> None:
    state = {
        "session_id": "cli",
        "user_query": query,
        "history": [],
        "retrieved_docs": [],
    }

    print(f"질문: {query}\n분류 중...")
    result = await classify_node(state)

    print(f"  case_type            : {result['case_type']}")
    print(f"  needs_settlement     : {result['needs_settlement']}")
    print(f"  classification_confidence: {result['classification_confidence']:.2f}")

    if result["classification_confidence"] < CLARIFY_THRESHOLD:
        print("  → 신뢰도 낮음: clarify_node 로 분기 예정")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python -m scripts.run_classify "질문 내용"')
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
