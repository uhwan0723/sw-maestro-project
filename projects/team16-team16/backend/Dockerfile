# syntax=docker/dockerfile:1.7
# 멀티 스테이지: deps 단계에서 uv로 의존성 동기화 → runtime에 .venv만 복사

# uv 이미지를 명시적 stage로 받아둔다 (BuildKit mount 충돌 회피)
FROM ghcr.io/astral-sh/uv:0.5.4 AS uv-bin

FROM python:3.11-slim AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# uv 설치
COPY --from=uv-bin /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
# dev 그룹 제외, 잠금 파일 기준 결정론적 설치
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 앱 코드 복사 후 자기 자신 설치 (editable 아님)
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=deps /app /app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
