from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Ideation Context Hub"
    database_url: str = Field("sqlite:///./data/ideation_context_hub.sqlite3", alias="ICH_DATABASE_URL")
    llm_provider: str = Field("auto", alias="ICH_LLM_PROVIDER")
    upstage_api_key: str = Field("", validation_alias=AliasChoices("ICH_UPSTAGE_API_KEY", "UPSTAGE_API_KEY"))
    claude_api_key: str = Field("", validation_alias=AliasChoices("ICH_CLAUDE_API_KEY", "ANTHROPIC_API_KEY"))
    codex_oauth_token: str = Field("", alias="ICH_CODEX_OAUTH_TOKEN")
    notion_token: str = Field("", alias="ICH_NOTION_TOKEN")
    github_token: str = Field("", alias="ICH_GITHUB_TOKEN")
    slack_token: str = Field("", alias="ICH_SLACK_TOKEN")
    linear_token: str = Field("", alias="ICH_LINEAR_TOKEN")
    mcp_server_url: str = Field("", alias="ICH_MCP_SERVER_URL")
    mcp_access_token: str = Field("", alias="ICH_MCP_ACCESS_TOKEN")
    langgraph_deployment_url: str = Field(
        "",
        validation_alias=AliasChoices("ICH_LANGGRAPH_DEPLOYMENT_URL", "LANGGRAPH_DEPLOYMENT_URL"),
    )
    langsmith_api_key: str = Field("", validation_alias=AliasChoices("ICH_LANGSMITH_API_KEY", "LANGSMITH_API_KEY"))
    langgraph_qa_assistant_id: str = Field(
        "",
        validation_alias=AliasChoices("ICH_LANGGRAPH_QA_ASSISTANT_ID", "LANGGRAPH_QA_ASSISTANT_ID"),
    )
    langgraph_review_assistant_id: str = Field(
        "",
        validation_alias=AliasChoices("ICH_LANGGRAPH_REVIEW_ASSISTANT_ID", "LANGGRAPH_REVIEW_ASSISTANT_ID"),
    )

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
