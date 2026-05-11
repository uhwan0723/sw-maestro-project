# Scenario Matrix

Use these cases for smoke testing app behavior, prompts, and harness output.

| ID | Input | Expected Classification | Key Checks |
| --- | --- | --- | --- |
| S1 | `KSPO DOME` | venue_name | venue basics, transit, entry notes, official-check section |
| S2 | `KSPO DOME 콘서트 준비물` | concert_with_venue_hint | checklist emphasis, source labels, latest official check |
| S3 | `블루스퀘어` | venue_name | local venue coverage and supported-venue wording |
| S4 | `예스24라이브홀 스탠딩` | venue_with_detail_question | standing-specific uncertainty and official-check wording |
| S5 | unknown small venue | unsupported_or_ambiguous | ask for more detail or say MVP venue support is limited |
| S6 | search API error | provider_failure | local-data fallback and transparent missing-web-evidence note |
| S7 | official source conflicts with public review | conflict | official source wins, public review stays reference-only |
| S8 | frontend guide request | ui_to_api_boundary | frontend submits to backend endpoint and does not call agent directly |
| S9 | backend guide request | api_to_agent_boundary | backend returns output contract from agent workflow |
| S10 | `아이유 콘서트 KSPO` | concert_with_venue_hint | infers KSPO DOME from venue hint and preserves original concert query in search |
| S11 | `아이유 콘서트` with search result mentioning only `KSPO DOME` | concert_with_inferred_venue | infers venue from public search evidence and avoids guessing when multiple MVP venues appear |
| S12 | `워터밤` with search results for Seoul and Incheon | event_candidates | returns multiple event candidates and asks the user to choose a region/date |

## Minimum Demo Pass

- Run at least S1, S2, S5, S6, S10, S11, and S12 before demo delivery.
- Run architecture boundary tests before demo delivery.
- Include exact command output or screenshots in `_workspace/04_demo-qa_report.md` when app code exists.
- For documentation-only changes, verify structure with `python3 scripts/validate_harness.py`.
