# Request Summary

## Issue

- GitHub issue: #40 `chore: 프론트엔드/백엔드/AI 통합 docker compose 환경 구성`
- Branch: `chore/docker-compose-setup`

## Scope

- Add Docker Compose support for running frontend and backend together.
- Keep the agent workflow inside the backend service, matching the existing application boundary.
- Avoid modifying existing Python application code unless required.
- Surface optional KOPIS, public search, Gemini, cache, timeout, and logging environment variables.
- Document local Compose startup, URLs, and host port overrides.

## Validation Plan

- `python3 scripts/validate_harness.py`
- `uv run --python 3.11 pytest`
- `docker compose config`
- Docker build/start smoke when Docker is available
