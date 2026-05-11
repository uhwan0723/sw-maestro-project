---
name: performation-source-research
description: Plan and review public web search, source classification, deduplication, and evidence handoffs for Performation.
---

# Performation Source Research

Use this skill for search query design, public web evidence collection, source classification, deduplication, and search-provider fallback behavior.

## Required Inputs

- user input or scenario
- supported venue data
- search provider constraints
- `docs/harness/performation/output-contract.md`

## Workflow

1. Classify the user input as concert name, venue name, or detail question.
2. Generate search queries that separate official pages from public review pages.
3. Prefer sources in this order: venue official page, ticket seller or event notice, public data or transit source, public blogs or reviews, public-search-discovered SNS tip snippets, general search snippets.
4. Deduplicate near-identical results before synthesis.
5. Tag every evidence item with one source type:
   - `official_confirmed`
   - `public_review_reference`
   - `latest_official_check_required`
   - `uncertain`
6. Write `_workspace/02_source-research_evidence.md` when evidence collection affects implementation, prompts, or demo output.

## Search Boundaries

- Allowed: public web search through Tavily, Brave Search, or equivalent MCP/API.
- Allowed: official venue pages, ticketing pages, public notices, public blogs, public search results.
- Allowed: official SNS links discovered through public search result metadata/snippets, used as latest-check channels.
- Allowed: public-review/SNS snippets discovered through public search, used only as anecdotal `후기 참고:` practical tips.
- Excluded: direct crawling of X, Instagram, Threads, or login-restricted platforms.
- Excluded: scraping copyrighted seat-view image collections for the MVP.

## Failure Behavior

- If the search provider fails, record the error category and return local venue data only.
- If results are sparse, mark missing evidence clearly.
- If public reviews conflict with official information, official information wins.
- If public tips are used, keep them labeled as reference and avoid presenting them as official operations.

## Validation

- every summarized claim can trace back to a source item or local venue data
- source types are not collapsed into one generic "source" bucket
- event-specific claims are not treated as stable venue facts
