---
name: performation-orchestrator
description: Coordinate Performation feature, data, search, trust-review, and demo-QA work from request to verified delivery.
---

# Performation Orchestrator

Use this skill for end-to-end work on the Performation project, especially when a task touches multiple surfaces such as FastAPI, Gradio, LangGraph, search integration, venue data, prompts, or demo verification.

## Required Inputs

- user request
- `AGENTS.md`
- `docs/project-brief.md`
- `docs/harness/performation/team-spec.md`
- current repository state
- any relevant `_workspace/` handoffs

## Workflow

1. Classify the request as one or more of: app implementation, venue data, source/search integration, prompt/output contract, trust review, QA, or docs.
2. Write or update `_workspace/00_input/request-summary.md` for non-trivial work.
3. Choose the smallest specialist set:
   - venue schema or fixture work: use `performation-venue-data`
   - search query, source classification, or evidence collection: use `performation-source-research`
   - confidence labels, official-vs-review conflicts, or safety wording: use `performation-trust-review`
   - demo scenarios, API/UI verification, or failure flows: use `performation-demo-qa`
4. Preserve the planned stack unless the user explicitly changes it: FastAPI, Gradio, LangGraph, Tavily or Brave Search style public search, file/in-memory data first.
5. Keep all user-facing guide output aligned with `docs/harness/performation/output-contract.md`.
6. Run `python3 scripts/validate_harness.py` after harness edits. When app code exists, also run the repo's exact tests and scenario checks.
7. Summarize changed files, validation commands, and residual risks in `_workspace/final/delivery-summary.md` when useful.

## Quality Bar

- Official source information must outrank public reviews.
- Event-specific or changing information must be labeled `latest_official_check_required`.
- Search failures must degrade to local venue data instead of fabricated web findings.
- Unsupported features must stay out of scope: SNS login crawling, ticketing, payments, real-time crowding, real-time merch stock, and seat-view image collection.

## Outputs

- implementation or documentation changes requested by the user
- preserved `_workspace/` handoffs for complex tasks
- verification evidence with exact commands run

## Validation

For harness-only changes:

```bash
python3 scripts/validate_harness.py
```

For app changes, add and run the project test commands once the app scaffold exists.
