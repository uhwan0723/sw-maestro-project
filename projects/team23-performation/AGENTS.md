# Repository Agents Guide

Keep this file short and repo-wide. Put role-specific workflow details in the harness docs and skills linked below.

## What

- Performation is a local Agentic Workflow demo that creates concert and venue visit-prep guides from venue data, KOPIS official performance data, and public web information.
- Planned stack: Gradio frontend, FastAPI backend, LangGraph workflow, KOPIS, Tavily or Brave Search, and file-based or in-memory venue data for the MVP.
- Application boundary: frontend calls backend API only; backend owns agent execution; agent packages must not depend on frontend or backend frameworks.
- Canonical harness artifacts live in `docs/harness/performation/` and `.agents/skills/performation-*`.
- Codex can discover the same workflow through `.codex/skills/`; Claude Code compatibility cards live in `.claude/agents/`.

## Why

- The product promise is practical: help first-time concertgoers find entry, transit, locker, preparation, source, and official-check information without visiting many search channels manually.
- The core safety boundary is source confidence. Official sources must be separated from public reviews, and uncertain or event-specific information must be marked as requiring latest official confirmation.
- MVP scope is intentionally narrow: KSPO DOME, Blue Square, YES24 Live Hall, KOPIS official performance lookup, public web search, and no SNS login crawling, ticketing, payments, seat-view image collection, real-time crowding, or real-time merch stock.

## How

- Before implementation or review, read `docs/project-brief.md` and `docs/harness/performation/team-spec.md`.
- Use `_workspace/` for deterministic phase handoffs and review evidence.
- Use the `performation-orchestrator` skill for end-to-end feature work, and route focused work to the specialist skills under `.agents/skills/performation-*`.
- Verify harness structure with `python3 scripts/validate_harness.py`.
- Run app tests with `uv run --python 3.11 pytest`.
- Run the backend with `PYTHONPATH=apps/backend/src:packages/agent/src:packages/domain/src:packages/venue-data/src uv run --python 3.11 uvicorn performation_backend.main:app --reload`.
- Run the frontend with `PYTHONPATH=apps/frontend/src uv run --python 3.11 python -m performation_frontend.app`.
- Before committing, follow `docs/harness/performation/git-policy.md`; use commit messages like `feat: 한글 요약`, `fix: 한글 요약`, or `test: 한글 요약`.
