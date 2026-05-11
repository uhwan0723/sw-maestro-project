from __future__ import annotations

from app.schemas.consultation import AgentId, ErrorCode, ErrorEvent, PublicError


def to_public_error(error: ErrorEvent) -> PublicError:
    affected_agent = _extract_agent_id(error.where)
    return PublicError(
        code=error.code,
        user_message_key=f"error.{error.code.value.lower()}",
        affected_agent=affected_agent,
    )


def _extract_agent_id(where: str) -> AgentId | None:
    for agent_id in AgentId:
        if agent_id is AgentId.SUPERVISOR:
            continue
        if agent_id.value in where:
            return agent_id
    return None
