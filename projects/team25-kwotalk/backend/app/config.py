"""환경 변수 + 경로 설정."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    upstage_api_key: str = os.getenv("UPSTAGE_API_KEY", "")
    index_dir: str = os.getenv("INDEX_DIR", "data/indices")
    guides_path: str = os.getenv("GUIDES_PATH", "data/guides.yaml")
    allowed_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
