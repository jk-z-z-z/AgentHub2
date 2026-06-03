from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentHub Backend"
    env: str = "local"
    api_prefix: str = "/api/v1"
    db_url: str = "sqlite:///./agenthub.db"
    data_root: str = "~/.multiproj-agent"
    skill_pool_dir: str = "./skill-pool"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"])
    openai_api_key: str = ""
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_model: str = "qwen3.6-plus"
    default_ai_system_prompt: str = "You are a helpful AI assistant."
    project_command_timeout_seconds: int = 120
    ai_short_term_history_limit: int = 50
    memory_compress_trigger_tokens: int = 3500
    memory_compress_keep_recent_messages: int = 12
    acp_codex_command: str = "npx -y @zed-industries/codex-acp"
    acp_claude_command: str = "python -m claude_code_acp"

    model_config = SettingsConfigDict(
        env_prefix="AGENTHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
