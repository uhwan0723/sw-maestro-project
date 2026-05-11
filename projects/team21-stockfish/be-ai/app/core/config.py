from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str
    cors_allowed_origins: list[str]
    naver_client_id: str | None = None
    naver_client_secret: str | None = None
    naver_news_display: int = Field(default=100, ge=1, le=100)
    enable_daily_collection_scheduler: bool = False
    daily_collection_hour: int = Field(default=18, ge=0, le=23)
    upstage_api_key: str | None = None
    upstage_base_url: str = "https://api.upstage.ai/v1"
    upstage_model: str = "solar-pro3"
    chat_history_max_turns: int = Field(default=5, ge=0, le=50)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
