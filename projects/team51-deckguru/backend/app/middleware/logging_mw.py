import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "-")
        start = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        logger.info(
            "request_start",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "request_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                latency_ms=latency_ms,
                error=str(exc),
            )
            structlog.contextvars.clear_contextvars()
            raise
        latency_ms = int((time.perf_counter() - start) * 1000)

        cache_status = response.headers.get("X-Cache", "-")
        logger.info(
            "request_done",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            cache=cache_status,
        )
        structlog.contextvars.clear_contextvars()
        return response
