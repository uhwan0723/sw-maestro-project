# Performation Output Contract

Generated user-facing guides should use this stable shape unless the product UI explicitly changes it.

## Guide Shape

```json
{
  "input": "KSPO DOME 콘서트 준비물",
  "input_type": "concert_with_venue_hint",
  "venue": {
    "name": "KSPO DOME",
    "address": "",
    "nearest_station": "",
    "transit_notes": []
  },
  "event_info": null,
  "event_candidates": [],
  "summary": [],
  "checklist": [],
  "transit_and_entry_tips": [],
  "official_check_required": [],
  "sources": [
    {
      "title": "",
      "url": "",
      "source_type": "official_confirmed",
      "used_for": []
    }
  ],
  "confidence_notes": []
}
```

## Required User-Facing Sections

- 공연장 기본 정보
- 공연 정보 (when `event_info` is not null)
- 공연 후보 (when `event_candidates` is not empty)
- 관람 전 핵심 요약
- 준비물 체크리스트
- 교통 및 입장 팁
- 공식 확인 필요 항목
- 참고 출처

## Input Types

| Value | Meaning |
| --- | --- |
| `venue_name` | supported MVP venue name or alias |
| `venue_with_detail_question` | supported venue plus a detail question such as entry, standing, transit, locker, or preparation |
| `concert_with_venue_hint` | concert-like input that includes a supported venue alias or hint |
| `concert_with_inferred_venue` | concert-like input where a single supported venue was inferred from public search results |
| `event_candidates` | broad or ambiguous event input where multiple event candidates should be offered for user selection |
| `unsupported_or_ambiguous` | no supported venue can be inferred safely |

## Event Candidate Shape

```json
{
  "name": "워터밤 서울",
  "region": "서울",
  "date_text": "2026년 7월",
  "venue_name": "확인 필요",
  "confidence_label": "latest_official_check_required",
  "sources": []
}
```

## Event Info Shape

```json
{
  "title": "EK 3rd Concert : You Good?",
  "date_text": "2026.05.10",
  "time_text": "18:00",
  "venue_name": "YES24 Live Hall",
  "confidence_label": "official_confirmed",
  "sources": []
}
```

## Source Types

| Label | Meaning | Examples |
| --- | --- | --- |
| `official_confirmed` | official or public-data source | venue site, ticket seller, KOPIS, public transport or public-data page |
| `public_review_reference` | anecdotal open web source | public blog, open review, guide post, public-search-discovered SNS tip snippet |
| `latest_official_check_required` | may change by event/date/operator | entry gate, locker operation, ID check, standing rules, official SNS notice link |
| `uncertain` | sparse, conflicting, or low-quality evidence | one-off result, unclear source, contradiction without official anchor |

## Wording Rules

- Never say public-review information is official.
- Never treat an SNS domain alone as official; use it as a latest-check channel only when the search result indicates an official account or notice.
- Public-review or SNS practical tips must be phrased as reference, preferably starting with `후기 참고:`.
- Prefer "공식 확인 필요" or "공연별 변동 가능성 있음" for event-specific operations.
- If search fails, say public search evidence could not be used and continue with local venue data only.
- Do not mention unsupported actions as available features.
