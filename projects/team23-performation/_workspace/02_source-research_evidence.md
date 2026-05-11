# Source Research Evidence

## Scope

- Inputs checked: `랩비트 페스티벌`, `워터밤`, `EK 콘서트`, KOPIS OpenAPI contract
- Goal: verify whether generated event candidates match current public/official evidence and define KOPIS as an official performance data source.
- SNS extension: handle official SNS notice links found through public search result metadata/snippets without direct SNS crawling.
- Public-review tip extension: use blog/review/SNS snippets found through public search for practical visit tips while keeping them anecdotal.

## SNS Source Contract

- Search query suffix: `공식 SNS 공지`
- Public-review query suffixes: `관람 후기 꿀팁`, `입장 대기 스탠딩 후기`, `물품보관 퇴장 교통 후기`
- Allowed input: public search result title, URL, and snippet from SNS domains.
- Excluded input: authenticated SNS pages, comments, profile crawling, infinite scroll scraping, or login-gated content.
- Classification:
  - official SNS notice/account hint -> `latest_official_check_required`
  - generic SNS post without official hint -> `uncertain`
  - fan, vlog, review, or repost-style SNS result -> `public_review_reference`
  - public blog/review/SNS practical tips -> `public_review_reference`
- Tip synthesis:
  - use only title/snippet/query metadata returned by the search provider
  - express tips with `후기 참고:` so they are not mistaken for official operations
  - supported tip categories: entry/standing, locker, exit/transit, preparation
  - official sources still win when review tips conflict with official notices

## KOPIS Contract

- KOPIS performance list endpoint: `http://www.kopis.or.kr/openApi/restful/pblprfr`
- KOPIS performance detail endpoint: `http://www.kopis.or.kr/openApi/restful/pblprfr/{공연아이디}`
- Required list parameters include `service`, `stdate`, `eddate`, `cpage`, and `rows`; `shprfnm` filters by performance name.
- KOPIS returns XML and includes fields such as `mt20id`, `prfnm`, `prfpdfrom`, `prfpdto`, `fcltynm`, `area`, `genrenm`, and `prfstate`.
- KOPIS evidence should be classified as `official_confirmed`; KOPIS failure should not block public search or local venue fallback.

## Findings

| Input | Candidate | Verdict | Evidence |
| --- | --- | --- | --- |
| `랩비트 페스티벌` | `랩비트 서울`, `2026년 6월 20일~21일`, `서울 마포 문화비축기지` | Valid | RAPBEAT official FAQ says RAPBEAT 2026 is at 문화비축기지 in 서울 마포구, and NOL ticket page lists period `2026.06.20 ~ 2026.06.21` with venue 문화비축기지. |
| `워터밤` | `워터밤 서울`, `2026년 7월 24일~26일`, `킨텍스 야외 글로벌 스테이지` | Valid | WATERBOMB official post confirms Seoul 2026 dates, and official tour page lists KINTEX Outdoor Global Stage. |
| `워터밤` | `워터밤 부산`, `2026년 8월 7~9일`, venue blank | Valid with venue pending | WATERBOMB official post confirms Busan 2026 dates. TicketLink currently lists Busan venue as 추후 공지, so venue should stay blank/official-check-required. |
| `EK 콘서트` | `EK 3rd Concert : You Good?`, `2026.05.10`, `18:00`, `YES24 Live Hall` | Valid | EK official Instagram notice lists date `2026.05.10`, venue `YES24 LIVE HALL`, and ticket notice sources align with StagePick's `18:00` performance time. |
| `EK 콘서트` | `EK 3rd Concert: You Good?`, `2026년 5월 10일`, `예스24 라이브홀 (구. 악스코리아)` | Valid via KOPIS | Live KOPIS lookup returns the performance as official data and the workflow maps the venue alias to `YES24 Live Hall`. |
| `워터밤` | `워터밤 서울`, `2026년 7월 24일~26일`, `킨텍스` | Valid via KOPIS | Live KOPIS lookup returns the Seoul event as official data with performance venue `킨텍스`. |
| `워터밤` | `워터밤 속초`, `2026년 8월 22일`, `한화리조트 [설악 쏘라노]` | Valid via KOPIS | Live KOPIS lookup returns the Sokcho event as official data. |
| `랩비트 페스티벌` | none from KOPIS | KOPIS unavailable for this query | Live KOPIS lookup returned no list result, so this query still depends on public search evidence and fallback behavior. |
| `랩비트 페스티벌` | none from KOPIS after alias expansion | KOPIS unavailable for this query | Live KOPIS lookup with `랩비트`, `RAPBEAT`, `RAP BEAT`, `RAPBEAT FESTIVAL`, and `RAP BEAT FESTIVAL` returned no list result. A broad KOPIS date scan for 2026-06-20~2026-06-21 also did not include RAPBEAT. |

## Implementation Notes

- Removed stale/noisy historical candidates when current-year candidates exist for a yearless query.
- Candidate extraction now ignores detail-query search results such as locker/review snippets.
- Region extraction prefers title regions before address regions, so `TOUR SEOUL` is not misread as `고양` because of the KINTEX address.
- Public review/blog venue snippets are not trusted as venue names.
- `추후 공개`, `추후공지`, and `미정` are treated as missing venue values.
- Single inferred concert flows now extract `event_info` so date/time/venue can be shown separately from general venue guidance.
- KOPIS title filtering rejects short ASCII false positives such as `EK` matching inside `WEEK` or `NEKIRU`.
- KOPIS event candidates include non-MVP regional options when official title regions are present, such as `워터밤 [속초]`.
- KOPIS search now expands known Korean event aliases, so `랩비트` also tries `RAPBEAT`, `RAP BEAT`, `RAPBEAT FESTIVAL`, and `RAP BEAT FESTIVAL`.
- Official SNS notice results can feed candidate/event extraction, but remain latest-check evidence instead of becoming `official_confirmed`.
- Public review/SNS tip results feed only practical tips, not official facts or venue/event extraction.
