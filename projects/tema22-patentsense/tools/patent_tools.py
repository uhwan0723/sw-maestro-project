import os
from pathlib import Path
import numpy as np
from langchain_core.tools import tool
from openai import OpenAI
from dotenv import load_dotenv

from tools.kipris import (
    search_patents as _search_patents,
    get_patent_detail as _get_patent_detail,
    get_representative_image as _get_representative_image,
    fetch_image_as_base64 as _fetch_image_as_base64,
)

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def _solar_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("SOLAR_API_KEY"),
        base_url="https://api.upstage.ai/v1",
    )


@tool
def search_patent_tool(keyword: str) -> list[dict]:
    """KIPRIS 특허 데이터베이스에서 키워드로 특허를 검색합니다.

    Args:
        keyword: 검색할 기술 키워드

    Returns:
        특허 목록 (출원번호, 제목, 출원인, 초록 등 포함)
    """
    try:
        return _search_patents(keyword, count=10)
    except RuntimeError:
        return []


@tool
def get_claim_tool(application_number: str) -> str:
    """특허 출원번호로 청구항을 조회합니다.
    청구항은 특허에서 법적으로 보호받는 기술 범위를 정의합니다.

    Args:
        application_number: 특허 출원번호

    Returns:
        청구항 텍스트 (없으면 빈 문자열)
    """
    try:
        detail = _get_patent_detail(application_number)
        return detail.get("claim", "") or ""
    except RuntimeError:
        return ""


@tool
def get_representative_image_tool(application_number: str) -> dict:
    """특허 출원번호로 대표도면 이미지 URL을 조회합니다.

    Args:
        application_number: 특허 출원번호

    Returns:
        {'path': 썸네일 URL, 'large_path': 원본 URL}
    """
    try:
        return _get_representative_image(application_number)
    except Exception:
        return {"path": "", "large_path": ""}


@tool
def fetch_image_tool(image_url: str) -> str:
    """이미지 URL을 base64 데이터 URI로 변환합니다.
    KIPRIS 이미지를 인라인으로 표시하기 위해 사용합니다.

    Args:
        image_url: 이미지 URL

    Returns:
        base64 데이터 URI 문자열
    """
    return _fetch_image_as_base64(image_url)


@tool
def embed_query_tool(text: str) -> list[float]:
    """사용자 아이디어/쿼리 텍스트를 임베딩 벡터로 변환합니다.
    유사도 검색의 기준 벡터로 사용됩니다.

    Args:
        text: 임베딩할 텍스트

    Returns:
        임베딩 벡터 (float 리스트)
    """
    client = _solar_client()
    resp = client.embeddings.create(model="embedding-query", input=text)
    return resp.data[0].embedding


@tool
def embed_passage_tool(text: str) -> list[float]:
    """특허 문서 텍스트를 임베딩 벡터로 변환합니다.
    특허 제목+초록+청구항을 벡터화할 때 사용됩니다.

    Args:
        text: 임베딩할 특허 텍스트

    Returns:
        임베딩 벡터 (float 리스트)
    """
    client = _solar_client()
    resp = client.embeddings.create(model="embedding-passage", input=text)
    return resp.data[0].embedding


# agent에 등록할 tool 목록
PATENT_TOOLS = [
    search_patent_tool,
    get_claim_tool,
    get_representative_image_tool,
    fetch_image_tool,
    embed_query_tool,
    embed_passage_tool,
]
