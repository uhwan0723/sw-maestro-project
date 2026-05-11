FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml 2>/dev/null || \
    uv pip install --system --no-cache \
      fastapi uvicorn[standard] pydantic pydantic-settings \
      structlog slowapi cachetools aiosqlite httpx

COPY . .

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
