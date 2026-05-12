from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urlparse


SUPPORTED_SOURCE_TYPES = {
    "manual",
    "upload",
    "txt",
    "md",
    "pdf",
    "csv",
    "notion",
    "github",
    "slack",
    "linear",
    "mcp",
    "web",
}


def normalize_source_type(source_type: str | None, default: str = "manual") -> str:
    normalized = (source_type or default).strip().lower()
    return normalized if normalized in SUPPORTED_SOURCE_TYPES else normalized or default


def filename_from_source(title: str | None, source_type: str, source_url: str | None) -> str:
    if title and title.strip():
        return title.strip()

    parsed = urlparse(source_url or "")
    candidate = Path(parsed.path).name
    if candidate:
        return candidate

    extension = {
        "txt": "txt",
        "md": "md",
        "pdf": "pdf",
        "csv": "csv",
        "notion": "md",
        "github": "md",
        "slack": "md",
        "linear": "md",
        "mcp": "md",
    }.get(source_type, "txt")
    return f"{source_type}-source.{extension}"
