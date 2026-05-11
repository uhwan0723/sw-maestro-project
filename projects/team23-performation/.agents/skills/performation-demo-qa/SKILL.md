---
name: performation-demo-qa
description: Verify Performation harness, API, LangGraph workflow, Gradio UI, and MVP scenarios for demo readiness.
---

# Performation Demo QA

Use this skill for validation, smoke tests, scenario testing, and demo-readiness checks.

## Required Inputs

- `docs/harness/performation/scenario-matrix.md`
- current app code or docs
- exact run/test commands when app code exists
- latest `_workspace/` handoffs

## Workflow

1. For harness-only changes, run `python3 scripts/validate_harness.py`.
2. For app changes, run the repo's unit or integration tests once they exist.
3. Test at least these MVP scenarios before demo delivery:
   - `KSPO DOME`
   - `KSPO DOME 콘서트 준비물`
   - unsupported or ambiguous venue
   - search provider failure
4. Verify API, workflow, and UI surfaces separately when the app exists.
5. Verify frontend/backend/agent dependency direction: frontend calls backend only, backend invokes agent, and agent has no UI/API framework dependency.
6. Confirm every output includes source/confidence information or a transparent fallback note.
7. Write `_workspace/04_demo-qa_report.md` when QA evidence matters for delivery.

## QA Report Shape

```markdown
# Demo QA Report

## Commands
- `{command}` - pass | fail

## Scenarios
| ID | Input | Result | Notes |
| --- | --- | --- | --- |

## Risks
- {remaining risk}
```

## Acceptance Criteria

- supported venues return useful local basics
- search failures do not crash the guide flow
- unsupported venues do not pretend full support
- official-check items are visible
- confidence labels are present
- frontend has no direct agent, search-provider, or venue-data imports
- backend is the only app layer that invokes the agent workflow
