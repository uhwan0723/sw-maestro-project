"""CLI 로 generate_node 단독 실행 (mock 입력)."""
import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.agents.generate import generate_node

MOCK_STATE = {
    "session_id": "cli",
    "user_query": "술 마시고 운전하다 단속됐어요. 처벌이 어떻게 되나요?",
    "history": [],
    "case_type": "DRUNK_DRIVING",
    "needs_settlement": False,
    "classification_confidence": 0.95,
    "clarification_question": None,
    "retrieved_docs": [
        {
            "doc_id": "law_road_44",
            "type": "법령",
            "title": "도로교통법 제44조 (술에 취한 상태에서의 운전 금지)",
            "content": "누구든지 술에 취한 상태에서 자동차 등을 운전하여서는 아니 된다.",
            "case_types": ["DRUNK_DRIVING"],
            "score": 0.95,
            "settlement_amount": None,
        },
        {
            "doc_id": "law_road_148_2",
            "type": "법령",
            "title": "도로교통법 제148조의2 (벌칙 — 음주운전)",
            "content": "혈중알코올농도 구간별 처벌 규정.",
            "case_types": ["DRUNK_DRIVING"],
            "score": 0.91,
            "settlement_amount": None,
        },
    ],
    "guide_steps": [
        "음주측정 거부 시 가중처벌 (측정에 응하는 것이 일반적으로 유리)",
        "면허정지·취소 행정처분과 형사처벌이 별개로 진행됨을 인지",
        "동승자·동석자 진술 확보",
        "초범인 경우 양형 참작 자료(반성문·기부·교육 이수) 준비",
    ],
    "settlement": None,
    "answer_text": "",
    "citations": [],
    "confidence_score": 0.0,
    "recommend_lawyer": False,
    "situation_summary": None,
}


async def main() -> None:
    print("generate_node 실행 중 (mock 입력)...\n")
    result = await generate_node(MOCK_STATE)

    print("=== 생성된 답변 ===")
    print(result["answer_text"])
    print("\n=== 인용 마커 ===")
    for c in result["citations"]:
        print(f"  [{c['marker_idx']}] → {c['doc_id']}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs"
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"generate_{timestamp}.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"질문: {MOCK_STATE['user_query']}\n")
        f.write(f"case_type: {MOCK_STATE['case_type']}\n")
        f.write("=" * 60 + "\n\n")
        f.write(result["answer_text"])
        f.write("\n\n" + "=" * 60 + "\n인용 마커\n")
        for c in result["citations"]:
            f.write(f"  [{c['marker_idx']}] → {c['doc_id']}\n")

    print(f"\n저장 완료: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
