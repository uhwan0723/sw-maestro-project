# syntax=docker/dockerfile:1.7
# 멀티 스테이지: deps 단계에서 uv로 의존성 동기화 → runtime에 .venv만 복사

FROM ghcr.io/astral-sh/uv:0.5.4 AS uv-bin

FROM python:3.11-slim AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=uv-bin /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=deps /app/.venv /app/.venv
COPY app ./app
COPY streamlit_app.py ./
COPY .streamlit ./.streamlit

EXPOSE 8002
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8002", "--server.address=0.0.0.0"]
