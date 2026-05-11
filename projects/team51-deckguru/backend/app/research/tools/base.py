"""Live Research 도구 공통 값과 예외.

각 도구(web_search/fetch_page/youtube_transcript)는 외부 네트워크에 의존한다.
실패했을 때 일반 예외를 흘려보내면 graph 쪽에서 구분하기 어렵기 때문에,
복구 가능한 도구 실패는 `ResearchToolError`로 통일한다.
"""

from __future__ import annotations

import os


# 외부 사이트가 어떤 클라이언트인지 식별할 수 있도록 User-Agent를 명시한다.
# 운영 환경에서 연락처를 넣고 싶으면 RESEARCH_USER_AGENT로 override한다.
USER_AGENT = os.getenv("RESEARCH_USER_AGENT", "DeckGuru/1.0 (research)")


class ResearchToolError(RuntimeError):
    """외부 research 도구가 복구 가능한 방식으로 실패했음을 나타내는 예외."""
