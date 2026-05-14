from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sales:sales@localhost:5432/sales"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    firecrawl_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    n8n_webhook_url: str = "http://localhost:5678/webhook"
    internal_api_token: str = "change-me-at-least-32-chars-random"
    next_public_api_base: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
