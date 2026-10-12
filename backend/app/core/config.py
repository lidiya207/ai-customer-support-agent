from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    APP_NAME: str = "AI Customer Support Agent"
    APP_ENV: str = "development"
    DATABASE_URL: str = "mysql+pymysql://root:password@127.0.0.1:3306/ai_support"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # ollama | openai | auto (openai if API key set, else ollama)
    LLM_PROVIDER: str = "auto"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    # Local CPU inference can be slow on cold start; allow several minutes.
    OLLAMA_TIMEOUT_SECONDS: float = 300.0
    # Cap generated tokens so replies finish faster on CPU.
    OLLAMA_NUM_PREDICT: int = 128
    # Smaller context window = faster prompt eval on local models.
    OLLAMA_NUM_CTX: int = 2048
    # Keep the model loaded in memory between requests (Ollama keep_alive).
    OLLAMA_KEEP_ALIVE: str = "30m"

    # Allow the agent to look up public info on the internet.
    ENABLE_WEB_SEARCH: bool = True
    WEB_SEARCH_TIMEOUT_SECONDS: float = 8.0

    # Comma-separated list of allowed browser origins for CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    JWT_SECRET_KEY: str = "change-this-in-production-use-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Mini Telegram bot (long-polling). Leave empty to disable.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_HISTORY_LIMIT: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
