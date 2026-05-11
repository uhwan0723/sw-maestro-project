from __future__ import annotations

import os

import httpx
from performation_domain import ErrorResponse, GuideRequest, GuideResponse

API_URL = os.getenv("PERFORMATION_API_URL", "http://127.0.0.1:8000").rstrip("/")

_client = httpx.Client(base_url=API_URL, timeout=30.0)


class PerformationAPIError(Exception):
  pass


def get_guide(query: str) -> GuideResponse:
  try:
    request_data = GuideRequest(query=query)
  except ValueError as exc:
    raise PerformationAPIError(f"유효하지 않은 입력입니다: {exc}")

  try:
    response = _client.post(
      "/guides",
      json=request_data.model_dump(),
    )

    if not response.is_success:
      try:
        error_data = ErrorResponse.model_validate(response.json())
        detail_msg = f" ({error_data.detail})" if error_data.detail else ""
        raise PerformationAPIError(f"API 오류: {error_data.error_message}{detail_msg}")
      except Exception:
        response.raise_for_status()

    return GuideResponse.model_validate(response.json())
  except httpx.HTTPError as exc:
    raise PerformationAPIError(f"백엔드 API 호출에 실패했습니다: {exc}") from exc
  except Exception as exc:
    raise PerformationAPIError(f"데이터 처리 중 오류가 발생했습니다: {exc}") from exc
