from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class NewsItem(BaseModel):
    """전예준 모듈이 반환하는 개별 뉴스."""

    title: str = Field(..., description="기사 제목 (원문 그대로, 정치적 평가 금지)")
    summary: str = Field(..., description="한 줄 요약 (LLM 가공 결과 또는 원문 첫 문장)")
    url: HttpUrl = Field(..., description="원문 링크")
    published_at: datetime = Field(..., description="기사 발행 시각")


class NewsResult(BaseModel):
    """카테고리별 묶음. fetch_news는 카테고리 수만큼 이 객체를 리스트로 반환."""

    category: str = Field(..., description="요청한 카테고리명 (예: 'IT', '경제')")
    items: list[NewsItem] = Field(..., description="카테고리당 3~5건. 중복 제거된 상태")
