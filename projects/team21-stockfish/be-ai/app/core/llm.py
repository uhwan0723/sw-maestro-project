from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings


UPSTAGE_CHAT_COMPLETIONS_PATH = "/chat/completions"

ChatRole = Literal["system", "user", "assistant"]
StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)


class LLMClientError(RuntimeError):
    pass


class LLMConfigurationError(LLMClientError):
    pass


class LLMAPIError(LLMClientError):
    pass


class LLMResponseFormatError(LLMClientError):
    pass


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str

    def to_payload(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str | None
    finish_reason: str | None
    usage: LLMUsage | None
    raw_response: Mapping[str, Any]


class UpstageLLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or settings.upstage_api_key
        self._base_url = (base_url or settings.upstage_base_url).rstrip("/")
        self._model = model or settings.upstage_model
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_http_client = http_client is None

    async def __aenter__(self) -> "UpstageLLMClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def complete(
        self,
        messages: Sequence[ChatMessage | Mapping[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        api_key = self._get_api_key()
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [_message_to_payload(message) for message in messages],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = dict(response_format)

        try:
            response = await self._http_client.post(
                f"{self._base_url}{UPSTAGE_CHAT_COMPLETIONS_PATH}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            response_payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMAPIError(
                f"Upstage API returned HTTP {exc.response.status_code}: "
                f"{_read_error_message(exc.response)}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMAPIError("Failed to call Upstage API") from exc
        except ValueError as exc:
            raise LLMResponseFormatError("Upstage API returned invalid JSON") from exc

        if not isinstance(response_payload, Mapping):
            raise LLMResponseFormatError("Upstage API returned invalid payload")

        return _parse_completion_response(response_payload)

    async def complete_structured(
        self,
        messages: Sequence[ChatMessage | Mapping[str, str]],
        *,
        response_model: type[StructuredResponseT],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> StructuredResponseT:
        response = await self.complete(
            [
                _build_structured_output_instruction(response_model),
                *messages,
            ],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            parsed_content = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise LLMResponseFormatError(
                "Upstage API returned content that is not valid JSON"
            ) from exc

        try:
            return response_model.model_validate(parsed_content)
        except ValidationError as exc:
            raise LLMResponseFormatError(
                f"Upstage API response did not match {response_model.__name__}"
            ) from exc

    def _get_api_key(self) -> str:
        if not self._api_key:
            raise LLMConfigurationError("UPSTAGE_API_KEY is required")
        return self._api_key


def _message_to_payload(message: ChatMessage | Mapping[str, str]) -> dict[str, str]:
    if isinstance(message, ChatMessage):
        return message.to_payload()

    role = message.get("role", "")
    content = message.get("content", "")
    if role not in ("system", "user", "assistant") or not content:
        raise LLMResponseFormatError(
            "LLM messages must include role and content strings"
        )
    return {"role": role, "content": content}


def _build_structured_output_instruction(
    response_model: type[BaseModel],
) -> ChatMessage:
    schema = json.dumps(
        response_model.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return ChatMessage(
        role="system",
        content=(
            "Return only a JSON object that conforms to this JSON Schema. "
            f"Do not include markdown or extra text. Schema: {schema}"
        ),
    )


def _parse_completion_response(payload: Mapping[str, Any]) -> LLMResponse:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMResponseFormatError("Upstage API response is missing choices")

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LLMResponseFormatError("Upstage API response has invalid choice")

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise LLMResponseFormatError("Upstage API response is missing message")

    content = message.get("content")
    if not isinstance(content, str):
        raise LLMResponseFormatError("Upstage API response is missing content")

    finish_reason = first_choice.get("finish_reason")
    model = payload.get("model")

    return LLMResponse(
        content=content,
        model=model if isinstance(model, str) else None,
        finish_reason=finish_reason if isinstance(finish_reason, str) else None,
        usage=_parse_usage(payload.get("usage")),
        raw_response=payload,
    )


def _parse_usage(value: Any) -> LLMUsage | None:
    if not isinstance(value, Mapping):
        return None

    return LLMUsage(
        prompt_tokens=_read_optional_int(value, "prompt_tokens"),
        completion_tokens=_read_optional_int(value, "completion_tokens"),
        total_tokens=_read_optional_int(value, "total_tokens"),
    )


def _read_optional_int(value: Mapping[str, Any], key: str) -> int | None:
    raw_value = value.get(key)
    return raw_value if isinstance(raw_value, int) else None


def _read_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    if not isinstance(payload, Mapping):
        return response.text

    error = payload.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        if isinstance(message, str):
            return message

    message = payload.get("message") or payload.get("errorMessage")
    return message if isinstance(message, str) else response.text
