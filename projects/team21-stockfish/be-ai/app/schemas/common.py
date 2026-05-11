from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SourceInfo(BaseModel):
    title: str | None = None
    url: str
    provider: str | None = None
    published_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_url_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"url": value}
        return value


class WarningMessage(BaseModel):
    code: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    warnings: list[WarningMessage] = Field(default_factory=list)
