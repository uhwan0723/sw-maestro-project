"""백엔드 호출 래퍼. Streamlit은 동기 모델이라 httpx.Client(동기)로 충분하다.

도메인 예외로 변환하여 UI 레이어가 사용자 메시지로 그대로 사용할 수 있게 한다.
"""
import httpx

from app.config import BACKEND_URL, REQUEST_TIMEOUT_SECONDS
from app.schemas import BriefingRequest, BriefingResponse


class BackendError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한국어 메시지를 담는다."""


class BackendUnavailable(BackendError):
    pass


class BackendTimeout(BackendError):
    pass


class BackendValidationError(BackendError):
    pass


class BackendServerError(BackendError):
    pass


def fetch_briefing(req: BriefingRequest) -> BriefingResponse:
    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.post("/api/v1/briefing", json=req.model_dump())
    except httpx.ConnectError as exc:
        raise BackendUnavailable(
            "백엔드에 연결할 수 없습니다. 서버 실행 상태를 확인해 주세요."
        ) from exc
    except httpx.TimeoutException as exc:
        raise BackendTimeout(
            "백엔드 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."
        ) from exc

    if resp.status_code == 422:
        raise BackendValidationError(f"요청 형식 오류: {resp.text}")
    if resp.status_code >= 500:
        raise BackendServerError(
            f"백엔드 오류({resp.status_code}). 잠시 후 다시 시도해 주세요."
        )
    resp.raise_for_status()

    return BriefingResponse.model_validate(resp.json())


def check_health() -> bool:
    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=3.0) as client:
            return client.get("/api/v1/health").status_code == 200
    except httpx.HTTPError:
        return False
