from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentHub Backend"
    env: str = "local"
    api_prefix: str = "/api/v1"
    db_url: str = "sqlite:///./agenthub.db"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_prefix="AGENTHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
