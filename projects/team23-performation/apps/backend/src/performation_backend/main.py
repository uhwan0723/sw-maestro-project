from __future__ import annotations

import asyncio
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from performation_agent import generate_visit_guide
from performation_domain import ErrorResponse, GuideRequest, GuideResponse


logging.basicConfig(
  level=os.getenv("PERFORMATION_LOG_LEVEL", "INFO").upper() or "INFO",
  format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  force=True,
)
logger = logging.getLogger("performation.backend")

app = FastAPI(
  title="Performation API",
  description="Backend API that owns Performation agent workflow execution.",
  version="0.1.0",
)

_origins = os.getenv("PERFORMATION_CORS_ORIGINS", "*")
app.add_middleware(
  CORSMiddleware,
  allow_origins=[origin.strip() for origin in _origins.split(",")],
  allow_methods=["*"],
  allow_headers=["*"],
)

_AGENT_TIMEOUT = float(os.getenv("PERFORMATION_AGENT_TIMEOUT_SECONDS") or 30)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
  errors = exc.errors()
  logger.warning("입력값 유효성 검사 실패: %s", errors[0].get("msg") if errors else "unknown")
  return JSONResponse(
    status_code=400,
    content=ErrorResponse(
      error_message="입력값이 올바르지 않습니다.",
      detail=errors[0].get("msg") if errors else None,
    ).model_dump(),
  )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
  logger.exception("에이전트 실행 중 예외 발생: %s", exc)
  return JSONResponse(
    status_code=500,
    content=ErrorResponse(
      error_message="요청을 처리하는 중 오류가 발생했습니다.",
      detail=None,
    ).model_dump(),
  )


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


@app.post("/guides", response_model=GuideResponse)
@app.post("/analyze", response_model=GuideResponse)
async def create_guide(request: GuideRequest) -> GuideResponse | JSONResponse:
  logger.info("가이드 요청: query=%r", request.query)
  started = time.monotonic()

  try:
    # NOTE: 타임아웃 발생 시 스레드는 즉시 중단되지 않고 완료될 때까지 계속 실행됩니다
    # (Thread Leakage). generate_visit_guide가 async로 전환되면 해소 가능합니다.
    result: GuideResponse = await asyncio.wait_for(
      asyncio.to_thread(generate_visit_guide, request.query),
      timeout=_AGENT_TIMEOUT,
    )
    elapsed = time.monotonic() - started
    logger.info(
      "가이드 완료: query=%r elapsed=%.2fs fallback_used=%s",
      request.query,
      elapsed,
      result.fallback_used,
    )
    return result
  except asyncio.TimeoutError:
    elapsed = time.monotonic() - started
    logger.warning("가이드 타임아웃: query=%r elapsed=%.2fs", request.query, elapsed)
    return JSONResponse(
      status_code=504,
      content=ErrorResponse(
        error_message="요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        detail=None,
      ).model_dump(),
    )
