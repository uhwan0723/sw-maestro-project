"""프롬프트 파일 로딩 + 템플릿 슬롯 치환."""
import os

# backend/app/utils/prompt_loader.py → backend/app/prompts/
_PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts",
)


def load_prompt(name: str) -> str:
    """app/prompts/{name} 을 읽어 문자열로 반환."""
    path = os.path.join(_PROMPTS_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def fill_template(template: str, **kwargs) -> str:
    """{key} 슬롯을 kwargs 로 치환. None 값은 빈 문자열로."""
    for key, value in kwargs.items():
        template = template.replace(f"{{{key}}}", "" if value is None else str(value))
    return template
