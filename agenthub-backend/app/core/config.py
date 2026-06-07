from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentHub Backend"
    env: str = "local"
    api_prefix: str = "/api/v1"
    db_url: str = "sqlite:///./agenthub.db"
    reset_db_on_startup: bool = False
    data_root: str = "~/.multiproj-agent"
    skill_pool_dir: str = "./skill-pool"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"])
    jwt_secret_key: str = "agenthub-dev-secret-key-change-me-please-32chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7
    openai_api_key: str = ""
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_model: str = "qwen3.6-plus"
    default_ai_system_prompt: str = "You are a helpful AI assistant."
    project_command_timeout_seconds: int = 120
    execution_command_timeout_seconds: int = 600
    deployment_command_timeout_seconds: int = 1800
    ai_short_term_history_limit: int = 50
    memory_compress_trigger_tokens: int = 3500
    memory_compress_keep_recent_messages: int = 12
    acp_codex_command: str = "npx -y @zed-industries/codex-acp"
    acp_claude_command: str = "python -m claude_code_acp"
    docker_sandbox_default_image: str = "node:20-bookworm"
    docker_sandbox_memory_limit: str = "2g"
    docker_sandbox_cpu_limit: str = "2.0"
    command_output_limit_chars: int = 50000

    model_config = SettingsConfigDict(
        env_prefix="AGENTHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
