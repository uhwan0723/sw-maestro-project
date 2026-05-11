# Workspace Handoffs

Use this directory for deterministic intermediate artifacts created by agents and skills.

Recommended layout:

```text
_workspace/
├── 00_input/
│   └── request-summary.md
├── 01_venue-data_contract.md
├── 02_source-research_evidence.md
├── 03_trust-review_findings.md
├── 04_demo-qa_report.md
└── final/
    └── delivery-summary.md
```

Keep useful evidence here when it helps future agents understand what happened. Do not store secrets.
