FROM python:3.11-slim AS runtime

ARG UV_VERSION=0.11.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

COPY apps ./apps
COPY packages ./packages

FROM runtime AS backend

ENV PYTHONPATH="apps/backend/src:packages/agent/src:packages/domain/src:packages/venue-data/src"

EXPOSE 8000

CMD ["uvicorn", "performation_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS frontend

ENV PYTHONPATH="apps/frontend/src:packages/domain/src" \
    PERFORMATION_API_URL="http://backend:8000" \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT="7860"

EXPOSE 7860

CMD ["python", "-m", "performation_frontend.app"]
