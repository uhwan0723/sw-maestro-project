from collections.abc import Awaitable, Callable
from uuid import uuid4

from app.ai.graph import run_agent
from app.ai.state import AgentState
from app.core.config import settings
from app.models.enums import RequestType
from app.schemas.chat import ChatRequest, ChatResponse, ChatTurn


AgentRunner = Callable[[AgentState], Awaitable[AgentState]]

DEFAULT_OUT_OF_SCOPE_ANSWER = (
    "현재는 KOSPI 반도체/제약 섹터 분석과 경제 용어 설명만 지원합니다."
)


class ChatService:
    def __init__(
        self,
        *,
        agent_runner: AgentRunner = run_agent,
        max_history_turns: int | None = None,
    ) -> None:
        self._agent_runner = agent_runner
        self._max_history_turns = (
            max_history_turns
            if max_history_turns is not None
            else settings.chat_history_max_turns
        )

    async def respond(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or uuid4().hex
        history = self._trim_history(request.history)

        state = await self._agent_runner(
            AgentState(
                user_message=request.message,
                sector=request.sector,
                session_id=session_id,
                chat_history=history,
            )
        )
        return ChatResponse(
            request_type=state.request_type or RequestType.OUT_OF_SCOPE,
            answer=state.final_answer or DEFAULT_OUT_OF_SCOPE_ANSWER,
            safety_notice=state.safety_notice,
            warnings=state.warnings,
            session_id=session_id,
        )

    def _trim_history(self, history: list[ChatTurn]) -> list[ChatTurn]:
        if self._max_history_turns <= 0:
            return []
        return history[-self._max_history_turns :]
