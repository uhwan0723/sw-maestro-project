from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = "local"

    # Upstage Solar (팀 합의 — D1)
    upstage_api_key: str = ""
    upstage_model_recommend: str = "solar-pro2"
    upstage_model_meta: str = "solar-pro2"
    upstage_model_intent: str = "solar-mini"

    embedding_model: str = "BAAI/bge-m3"
    chroma_path: Path = Path("../data/rag/vectorstore/chroma")
    rag_min_score: float = 0.05
    patch_version: str = "17.2"
    live_research_enabled: bool = True
    live_research_timeout_s: float = 12.0
    live_research_max_steps: int = 2
    demo_mode: bool = False
    mock_strategy_agent: bool = False
    log_level: str = "INFO"
    app_log_format: str = Field(
        default="console",
        validation_alias=AliasChoices("APP_LOG_FORMAT", "DECKGURU_LOG_FORMAT"),
    )
    app_log_colors: bool = Field(
        default=True,
        validation_alias=AliasChoices("APP_LOG_COLORS", "DECKGURU_LOG_COLORS"),
    )
    admin_token: str = "dev-admin"
    tavily_api_key: str = ""

    agent_timeout_s: float = 40.0
    semaphore_limit: int = 8
    rate_limit_per_min: int = 5
    rate_limit_per_hour: int = 60
    cache_l1_size: int = 1000
    cache_l2_ttl_days: int = 7

    sqlite_path: Path = Path("./deckguru.db")

    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    @property
    def effective_rate_limit(self) -> str:
        if self.demo_mode:
            return "100/minute"
        return f"{self.rate_limit_per_min}/minute"


settings = Settings()
