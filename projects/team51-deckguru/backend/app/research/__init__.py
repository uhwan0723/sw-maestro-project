"""Live Research package public API.

외부 모듈은 가능하면 `app.research.api`의 구현 세부사항 대신 여기서 export한
`run_live_research`만 사용한다.
"""

from app.research.api import ResearchResult, run_live_research

__all__ = ["ResearchResult", "run_live_research"]
