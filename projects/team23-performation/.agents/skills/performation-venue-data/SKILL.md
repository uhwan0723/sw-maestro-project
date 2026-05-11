---
name: performation-venue-data
description: Design and maintain MVP venue data schemas, fixtures, and fixed venue tips for Performation.
---

# Performation Venue Data

Use this skill when creating or reviewing local venue data, JSON fixtures, in-memory repositories, venue lookup logic, or venue-specific fixed tips.

## Required Inputs

- `docs/project-brief.md`
- `docs/harness/performation/output-contract.md`
- existing venue data files, if any
- target MVP venue names: KSPO DOME, Blue Square, YES24 Live Hall

## Workflow

1. Keep the MVP venue set narrow unless the user asks to expand it.
2. Define data fields that the guide needs: venue name, aliases, address, nearest station, transit notes, entry notes, locker notes, convenience facilities, event-specific check items, and source references.
3. Store official or stable data separately from anecdotal tips.
4. Use source confidence labels from `docs/harness/performation/output-contract.md`.
5. When adding seed data, prefer explicit empty or `latest_official_check_required` fields over guessing.
6. Write the schema or data decision to `_workspace/01_venue-data_contract.md` for non-trivial changes.

## Output Contract

Venue data should make it easy for the app to produce:

- 공연장 기본 정보
- 교통 및 입장 팁
- 물품보관 관련 참고 정보
- 주변 편의시설
- 공연별 확인 필요 항목
- sources with confidence labels

## Validation

- supported venue names and aliases resolve deterministically
- unsupported venues return a clear MVP-limited response
- no field implies official certainty without an official source
- no out-of-scope fields promise ticketing, payment, SNS crawling, seat images, or real-time status
