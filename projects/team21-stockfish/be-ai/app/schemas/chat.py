from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import RequestType, SectorCode
from app.schemas.common import WarningMessage


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    sector: SectorCode | None = None
    session_id: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_type: RequestType
    answer: str
    safety_notice: str | None = None
    warnings: list[WarningMessage] = Field(default_factory=list)
    session_id: str | None = None
