from fastapi import APIRouter

from app.schemas.api import FeedbackRequest
from app.services.feedback_store import feedback_store

router = APIRouter()


@router.post(
    "/feedback",
    summary="추천 결과 피드백 제출",
    description="""
추천 결과에 대한 만족도 평가를 제출합니다.

- `request_id`: 평가 대상 추천 요청 ID (`X-Request-ID` 응답 헤더 값)
- `rating`: 1~5점 만족도
- `comment`: 선택 사항, 최대 500자
- `deck_clicked`: 유저가 클릭한 덱 이름 (선택 사항)

제출된 피드백은 SQLite에 저장됩니다.
""",
)
async def submit_feedback(body: FeedbackRequest):
    await feedback_store.save(body)
    return {"ok": True}
