from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.llm import (
    LLMAPIError,
    LLMClientError,
    LLMConfigurationError,
    LLMResponseFormatError,
)
from app.ingestion.naver_news_client import NaverNewsClientError
from app.ingestion.yfinance_client import YFinanceClientError
from app.schemas.common import ErrorDetail, ErrorResponse, WarningMessage


class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        field: str | None = None,
        warnings: Sequence[WarningMessage] = (),
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.warnings = tuple(warnings)
        super().__init__(message)


class AnalysisConfidenceError(APIError):
    def __init__(
        self,
        *,
        confidence: float,
        warnings: Sequence[WarningMessage] = (),
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="analysis_confidence_too_low",
            message=(
                "분석에 필요한 근거가 부족해 신뢰도 기준을 충족하지 못했습니다."
            ),
            warnings=(
                *warnings,
                WarningMessage(
                    code="analysis_confidence_too_low",
                    message=f"분석 신뢰도는 {confidence:.2f}입니다.",
                ),
            ),
        )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(LLMConfigurationError, _handle_llm_configuration_error)
    app.add_exception_handler(LLMResponseFormatError, _handle_llm_response_error)
    app.add_exception_handler(LLMAPIError, _handle_llm_api_error)
    app.add_exception_handler(LLMClientError, _handle_llm_api_error)
    app.add_exception_handler(NaverNewsClientError, _handle_external_api_error)
    app.add_exception_handler(YFinanceClientError, _handle_external_api_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)


async def _handle_api_error(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    error = _coerce_api_error(exc)
    return _build_error_response(
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        field=error.field,
        warnings=error.warnings,
    )


async def _handle_validation_error(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    validation_error = _coerce_validation_error(exc)
    first_error = validation_error.errors()[0] if validation_error.errors() else {}
    return _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="요청 입력값이 올바르지 않습니다.",
        field=_read_validation_field(first_error),
        warnings=_build_validation_warnings(first_error),
    )


async def _handle_llm_configuration_error(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="llm_configuration_error",
        message="LLM 설정이 올바르지 않습니다.",
    )


async def _handle_llm_response_error(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return _build_error_response(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="llm_response_format_error",
        message="LLM 응답 형식이 올바르지 않습니다.",
    )


async def _handle_llm_api_error(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return _build_error_response(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="llm_api_error",
        message="LLM API 호출에 실패했습니다.",
    )


async def _handle_external_api_error(
    _request: Request,
    _exc: Exception,
) -> JSONResponse:
    return _build_error_response(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="external_api_error",
        message="외부 데이터 API 호출에 실패했습니다.",
    )


async def _handle_http_error(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    http_error = _coerce_http_error(exc)
    return _build_error_response(
        status_code=http_error.status_code,
        code="http_error",
        message=_read_http_error_message(http_error),
    )


def _build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
    warnings: Sequence[WarningMessage] = (),
) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            field=field,
        ),
        warnings=list(warnings),
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


def _coerce_api_error(exc: Exception) -> APIError:
    if isinstance(exc, APIError):
        return exc
    raise TypeError("Expected APIError")


def _coerce_validation_error(exc: Exception) -> RequestValidationError:
    if isinstance(exc, RequestValidationError):
        return exc
    raise TypeError("Expected RequestValidationError")


def _coerce_http_error(exc: Exception) -> StarletteHTTPException:
    if isinstance(exc, StarletteHTTPException):
        return exc
    raise TypeError("Expected StarletteHTTPException")


def _read_validation_message(error: dict[str, Any]) -> str:
    message = error.get("msg")
    return message if isinstance(message, str) else "요청 입력값이 올바르지 않습니다."


def _read_validation_field(error: dict[str, Any]) -> str | None:
    location = error.get("loc")
    if not isinstance(location, tuple | list):
        return None
    return ".".join(str(part) for part in location)


def _build_validation_warnings(error: dict[str, Any]) -> tuple[WarningMessage, ...]:
    if not error:
        return ()
    return (
        WarningMessage(
            code="validation_detail",
            message=_read_validation_message(error),
        ),
    )


def _read_http_error_message(exc: StarletteHTTPException) -> str:
    detail = exc.detail
    return detail if isinstance(detail, str) else "요청을 처리할 수 없습니다."
