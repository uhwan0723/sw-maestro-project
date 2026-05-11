from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    upstage_api_key: str = ""
    upstage_model: str = "solar-pro2"
    upstage_base_url: str = "https://api.upstage.ai/v1"

    openweather_api_key: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""

    app_port: int = 8001
    allowed_origins: str = "http://localhost:8002,http://localhost:8501"

    cache_ttl: int = 600
    cache_maxsize: int = 128

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
