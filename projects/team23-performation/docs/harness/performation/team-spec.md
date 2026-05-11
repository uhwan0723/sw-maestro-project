# Performation Harness Team Spec

## Goal

Create and maintain a reusable agent team for the Performation MVP: a FastAPI, Gradio, and LangGraph demo that turns a concert or venue query into a sourced, confidence-labeled visit-prep guide.

## Architecture Pattern

Outer pattern: Supervisor.

Local quality gate: Producer-Reviewer.

Reasoning:

- the orchestrator must decide whether a request is implementation, data curation, source research, or QA
- source confidence and official-vs-review conflict handling require an explicit reviewer step
- most work still moves through a stable pipeline: scope -> data/search contract -> implementation -> review -> demo verification

## Inputs

- user request
- `docs/project-brief.md`
- current repository state
- monorepo surfaces under `apps/frontend`, `apps/backend`, `packages/agent`, `packages/domain`, and `packages/venue-data`
- any app code, fixture data, prompts, tests, and generated `_workspace/` handoffs
- approved KOPIS, public search API, or MCP configuration when search integration is implemented

## Outputs

- application or documentation changes requested by the user
- preserved handoffs under `_workspace/`
- validation notes with exact commands run
- commit plan or completed commit summary that follows `docs/harness/performation/git-policy.md` when the user asks for commits
- updated harness docs or skills when durable workflow assumptions change

## Roles

| Role | Responsibility | Reusable skill | Writes |
| --- | --- | --- | --- |
| Orchestrator | classify the request, choose specialists, preserve handoffs, and integrate final work | `.agents/skills/performation-orchestrator/SKILL.md` | `_workspace/00_input/request-summary.md`, `_workspace/final/delivery-summary.md` |
| Venue Data Curator | define and maintain local venue data, seed fixtures, and venue-specific fixed tips | `.agents/skills/performation-venue-data/SKILL.md` | `_workspace/01_venue-data_contract.md` |
| Source Researcher | design search queries, collect public results, classify source type, and dedupe evidence | `.agents/skills/performation-source-research/SKILL.md` | `_workspace/02_source-research_evidence.md` |
| Trust Reviewer | verify confidence labels, conflict handling, and uncertainty language | `.agents/skills/performation-trust-review/SKILL.md` | `_workspace/03_trust-review_findings.md` |
| Demo QA | test normal and failure flows across API, workflow, and UI surfaces | `.agents/skills/performation-demo-qa/SKILL.md` | `_workspace/04_demo-qa_report.md` |

## Application Boundary

Dependency direction:

```text
apps/frontend -> apps/backend -> packages/agent -> packages/venue-data
                                      |
                                      -> packages/domain
```

- `apps/frontend` owns Gradio UI and must call the backend API only.
- `apps/frontend` must not import `performation_agent`, `performation_venue_data`, LangGraph, or search clients directly.
- `apps/backend` owns FastAPI endpoints, request/response validation, and agent workflow invocation.
- `packages/agent` owns input classification, search orchestration, venue-data lookup, summarization, confidence labels, and checklist generation.
- `packages/agent` must not import FastAPI, Gradio, or frontend code.
- `packages/domain` owns shared request/response schema and confidence labels.
- `packages/venue-data` owns fallback venue fixtures and repository access.

## Phase Order

### Phase 1: Scope Snapshot

- input sources: user request, `AGENTS.md`, `docs/project-brief.md`, current repo files
- actions: classify the task, identify affected surfaces, record assumptions
- output files: `_workspace/00_input/request-summary.md`
- completion criteria: the request type, target files, and validation plan are explicit

### Phase 2: Data and Source Contract

- input sources: project brief, existing venue data, planned search provider
- actions: define local venue schema, KOPIS result shape, public search result shape, source categories, and confidence labels
- output files: `_workspace/01_venue-data_contract.md`, `_workspace/02_source-research_evidence.md` when research is performed
- completion criteria: downstream implementation can distinguish official data, public reviews, latest-check items, and uncertainty

### Phase 3: Implementation or Documentation

- input sources: Phase 1 and 2 handoffs, current codebase
- actions: implement requested change or update durable docs/skills
- output files: changed code/docs plus optional `_workspace/implementation-notes.md`
- completion criteria: output follows the planned stack, application dependency boundary, and source-confidence boundary

### Phase 4: Trust Review

- input sources: generated guide logic, prompts, source mapping, fixture data, API/UI output
- actions: check official-source precedence, uncertainty wording, source labels, and excluded actions
- output files: `_workspace/03_trust-review_findings.md`
- completion criteria: no guide presents public-review or unverified information as official fact

### Phase 5: Demo QA

- input sources: changed application/docs, test fixtures, scenario matrix
- actions: run structure checks, unit/integration tests when present, and MVP venue scenarios
- output files: `_workspace/04_demo-qa_report.md`
- completion criteria: normal flow, at least one failure flow, and frontend/backend/agent boundary checks have explicit evidence

### Phase 6: Delivery

- input sources: changed files and validation outputs
- actions: summarize user-facing changes, commands run, remaining gaps, next blocker, and commit grouping when commits are requested
- output files: `_workspace/final/delivery-summary.md`
- completion criteria: final answer can cite what changed and what was verified

## Handoff Files

| From | To | File | Purpose |
| --- | --- | --- | --- |
| Orchestrator | All roles | `_workspace/00_input/request-summary.md` | stable task scope and assumptions |
| Venue Data Curator | Implementation and QA | `_workspace/01_venue-data_contract.md` | local data schema and target venue coverage |
| Source Researcher | Implementation and Trust Reviewer | `_workspace/02_source-research_evidence.md` | query plan, source list, dedupe notes, source classes |
| Trust Reviewer | Orchestrator and QA | `_workspace/03_trust-review_findings.md` | approval or fix requests for confidence and safety |
| Demo QA | Orchestrator | `_workspace/04_demo-qa_report.md` | final verification evidence and residual risk |
| Orchestrator | User | `_workspace/final/delivery-summary.md` | concise delivery notes |

## Failure Policy

- Search API unavailable: return local venue-data guide only and mark web evidence unavailable.
- KOPIS API unavailable or unconfigured: skip official performance lookup and continue with public search plus local venue data.
- Provider cache disabled or cold: call the configured provider normally and cache only successful results.
- SNS source unavailable or login-gated: use only public search result metadata/snippets; present official SNS links as latest-check channels and public SNS/review tips as anecdotal references, not as directly crawled data.
- Sparse search results: say enough public information was not found and avoid inventing details.
- Concert-name-only input: infer an MVP venue from public search only when exactly one supported venue is found.
- Broad event input: when multiple regional/date candidates are found, return candidate options instead of forcing one guide.
- Official/public conflict: prefer official sources; keep public reviews as anecdotal reference.
- Ambiguous input: ask for venue name, event date, artist, or ticketing page only when a reasonable assumption would be risky.
- Review failure: apply one bounded fix loop, then report unresolved risks instead of repeatedly rewriting.
- Out-of-scope request: decline or defer ticketing, payments, login-based SNS crawling, real-time crowding, real-time merch stock, and seat-view image collection.

## Confidence Labels

- `official_confirmed`: official venue, ticket seller, announcement, or public-data source.
- `public_review_reference`: public blogs or open reviews used as anecdotal context.
- `latest_official_check_required`: event-specific or frequently changing information.
- `uncertain`: sparse, conflicting, or low-confidence evidence.

## Codex and Claude Compatibility

- Canonical generated skills live in `.agents/skills/performation-*`.
- Codex mirrors live in `.codex/skills/performation-*`.
- Claude Code agent cards live in `.claude/agents/performation-*.md`.
- Keep role names and confidence labels identical across all mirrors.

## Validation Checks

- `python3 scripts/validate_harness.py`
- `uv run --python 3.11 pytest`
- every generated `SKILL.md` has YAML frontmatter with `name` and `description`
- every project-specific shared skill has a Codex discovery mirror
- every role listed here has either a reusable skill or a Claude agent card
- frontend has no direct agent, venue-data, LangGraph, or search-provider imports
- backend is the only application layer that invokes the agent workflow
- normal-flow and failure-flow scenarios remain aligned with `docs/harness/performation/scenario-matrix.md`
- commit rules remain aligned with `docs/harness/performation/git-policy.md`

## Normal-Flow Scenario

Request:

```text
KSPO DOME 콘서트 준비물 알려줘
```

Expected:

- input is classified as a concert-like query with a supported venue hint
- local venue basics are used
- public web search is attempted if configured
- KOPIS official performance lookup is attempted for concert/event queries if configured
- output separates official venue/ticketing information from public blog/review tips
- checklist includes ticket, ID if needed, battery, arrival-time check, locker availability check, transit crowding warning, and official notice check

## Failure-Flow Scenario

Failure point: search provider returns an error or no relevant results.

Expected:

- response still provides local venue basics for supported venues
- output clearly marks public web evidence unavailable or insufficient
- event-specific items are labeled `latest_official_check_required`
