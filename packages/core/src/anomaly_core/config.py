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


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
