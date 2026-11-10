from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "anomaly-evidence"
    runner_image: str = "anomaly-runner:dev"
    runner_network: str = "anomaly-net"
    ai_provider: str = "ollama"
    ai_ollama_base_url: str = "http://localhost:11434"
    ai_ollama_model: str = "llama3.1"
    ai_openai_api_key: str = ""
    ai_openai_model: str = "gpt-4o-mini"
    ai_openai_base_url: str = "https://api.openai.com/v1"
    ai_anthropic_api_key: str = ""
    ai_anthropic_model: str = "claude-3-5-sonnet"
    ai_anthropic_base_url: str = "https://api.anthropic.com/v1"
    ai_request_timeout_s: int = 60


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
