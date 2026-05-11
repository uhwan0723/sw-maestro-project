import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import examples, feedback, health, internal, patch_info, recommend
from app.middleware.logging_mw import LoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.services.cache import cache_service
from app.services.feedback_store import feedback_store
from app.services.limiter import limiter
from app.settings import settings


def _log_level() -> int:
    level = logging.getLevelName(settings.log_level.upper())
    return level if isinstance(level, int) else logging.INFO


def _configure_logging() -> None:
    log_format = settings.app_log_format.lower()
    timestamp_format = "iso" if log_format == "json" else "%H:%M:%S"
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt=timestamp_format),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=settings.app_log_colors)
    )
    if log_format == "json":
        processors.append(structlog.processors.format_exc_info)
    processors.append(renderer)

    logging.basicConfig(format="%(message)s", level=_log_level())
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(_log_level()),
        processors=processors,
    )


_configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache_service.init_db()
    await feedback_store.init_db()
    yield


app = FastAPI(
    title="DeckGuru API",
    version="0.1.0",
    description="""
## DeckGuru — TFT 메타 분석 및 덱 추천 AI

티어 · 플레이 스타일 · 자연어 질문을 입력받아 **현재 패치 기준 덱 추천 + 운영법 + 출처 + 확신도**를 반환합니다.

### 핵심 원칙
- **Grounding-First**: 응답의 모든 기물·아이템명은 RAG 화이트리스트에 존재하는 것만 사용
- **Patch-Versioned**: 모든 데이터는 `patch_version` 기준으로 필터링
- **Source-Mandatory**: 외부 인용 사실은 `sources[]`와 1:1 대응

### 응답 헤더
| 헤더 | 설명 |
|------|------|
| `X-Request-ID` | 요청 추적 ID |
| `X-Cache` | `HIT` / `MISS` |
| `X-Patch-Version` | 응답 기준 패치 버전 |
""",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
    allow_credentials=False,
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "서버 오류가 발생했어요.", "request_id": req_id}},
    )


app.include_router(recommend.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(patch_info.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(examples.router, prefix="/api")
app.include_router(internal.router, prefix="/api")
