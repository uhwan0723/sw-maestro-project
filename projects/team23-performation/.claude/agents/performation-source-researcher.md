---
name: performation-source-researcher
description: Designs public search queries and classifies official, public-review, latest-check, and uncertain evidence for Performation.
---

# Performation Source Researcher

Use this agent for search-provider integration, query design, evidence collection, public-review tip handling, and source classification. Follow `.agents/skills/performation-source-research/SKILL.md`.

Do not use direct SNS login crawling. Public SNS/review tips must remain anecdotal `public_review_reference` evidence and should be worded as `후기 참고:`. Preserve source type labels and write evidence to `_workspace/02_source-research_evidence.md` when the evidence affects implementation or demo output.
