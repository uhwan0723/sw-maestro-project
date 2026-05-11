from fastapi import APIRouter

router = APIRouter()

_EXAMPLES = [
    {
        "intent": "recommend_deck",
        "text": "현재 패치에서 골드가 티어 올리기 좋은 덱 3개 추천해줘",
    },
    {
        "intent": "deck_playstyle",
        "text": "요즘 많이 나오는 덱 하나 골라서 초반부터 후반까지 운영법 알려줘",
    },
    {
        "intent": "item_pivot",
        "text": "초반에 곡궁이 많이 나왔는데 어떤 덱 가면 좋아?",
    },
    {
        "intent": "patch_summary",
        "text": "이번 롤토체스 패치에서 메타에 영향 큰 변경점만 알려줘",
    },
]


@router.get(
    "/example-questions",
    summary="예시 질문 목록",
    description="""
4가지 인텐트별 예시 질문을 반환합니다. 프론트엔드 입력창 힌트 텍스트로 활용합니다.

| intent | 설명 |
|--------|------|
| `recommend_deck` | 덱 추천 |
| `deck_playstyle` | 운영법 안내 |
| `item_pivot` | 아이템 기반 덱 탐색 |
| `patch_summary` | 패치 변경점 요약 |
""",
)
async def example_questions():
    return _EXAMPLES
