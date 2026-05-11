from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.llm import ChatMessage


PROMPT_DIR = Path(__file__).resolve().parent


class PromptTemplateError(ValueError):
    pass


def load_prompt_messages(prompt_name: str, **values: Any) -> list[ChatMessage]:
    messages = _load_prompt_messages(prompt_name)
    return [
        ChatMessage(
            role=role,
            content=_render_template(
                template=content,
                prompt_name=prompt_name,
                values=values,
            ),
        )
        for role, content in messages
    ]


@lru_cache
def _load_prompt_messages(prompt_name: str) -> tuple[tuple[str, str], ...]:
    prompt_path = PROMPT_DIR / f"{prompt_name}.yaml"
    try:
        payload = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptTemplateError(f"Prompt file not found: {prompt_path}") from exc

    if not isinstance(payload, dict):
        raise PromptTemplateError(f"Prompt payload must be a mapping: {prompt_path}")

    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise PromptTemplateError(f"Prompt messages must be a list: {prompt_path}")

    loaded_messages: list[tuple[str, str]] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise PromptTemplateError(
                f"Prompt message must be a mapping: {prompt_path}#{index}"
            )

        role = message.get("role")
        content = message.get("content")
        if role not in ("system", "user", "assistant"):
            raise PromptTemplateError(
                f"Prompt message has invalid role: {prompt_path}#{index}"
            )
        if not isinstance(content, str) or not content.strip():
            raise PromptTemplateError(
                f"Prompt message content must be a non-empty string: "
                f"{prompt_path}#{index}"
            )

        loaded_messages.append((role, content))

    return tuple(loaded_messages)


def _render_template(
    *,
    template: str,
    prompt_name: str,
    values: dict[str, Any],
) -> str:
    try:
        return template.format(**values)
    except KeyError as exc:
        missing_key = exc.args[0]
        raise PromptTemplateError(
            f"Prompt '{prompt_name}' is missing template value: {missing_key}"
        ) from exc
