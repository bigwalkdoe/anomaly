from __future__ import annotations

from anomaly_core.config import Settings


def test_ai_settings_defaults(monkeypatch):
    # Provide required fields so Settings can instantiate without relying on .env
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "miniosecret")

    s = Settings(_env_file=None)

    assert s.ai_provider == "ollama"
    assert s.ai_ollama_base_url == "http://localhost:11434"
    assert s.ai_ollama_model == "llama3.1"
    assert s.ai_openai_api_key == ""
    assert s.ai_openai_model == "gpt-4o-mini"
    assert s.ai_openai_base_url == "https://api.openai.com/v1"
    assert s.ai_anthropic_api_key == ""
    assert s.ai_anthropic_model == "claude-3-5-sonnet"
    assert s.ai_anthropic_base_url == "https://api.anthropic.com/v1"
    assert s.ai_request_timeout_s == 60
