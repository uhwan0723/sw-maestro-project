---
name: performation-trust-review
description: Review Performation guides, prompts, and data for source confidence, uncertainty wording, and out-of-scope behavior.
---

# Performation Trust Review

Use this skill whenever output quality depends on source confidence, official-vs-review conflicts, uncertainty wording, or safety boundaries.

## Required Inputs

- generated guide or prompt
- source evidence, if available
- local venue data, if available
- `docs/harness/performation/output-contract.md`
- original user request

## Review Checklist

- Official information is clearly separated from public reviews.
- Public review tips are marked as reference, not fact.
- Event-specific operations use `latest_official_check_required` or equivalent Korean wording.
- Sparse or conflicting information is labeled `uncertain`.
- The guide does not offer ticketing, payment, reservation, inquiry, SNS crawling, real-time crowding, real-time merch stock, or seat-image collection.
- The response stays practical for first-time concertgoers.

## Review Output

Write `_workspace/03_trust-review_findings.md` for substantial changes using:

```markdown
# Trust Review Findings

## Verdict
- pass | fix | redo

## Findings
- {issue, source, suggested fix}

## Required Fixes
- {bounded changes}

## Residual Risk
- {what remains uncertain}
```

## Decision Rules

- If an official source conflicts with a blog/review, require official-source wording.
- If there is no source, require either local-data attribution or uncertainty wording.
- If the output invents operational details, request a fix.
- If the output hides the need for latest official confirmation, request a fix.
