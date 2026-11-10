from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from anomaly_core.config import get_settings


@dataclass
class AIMessage:
    role: str
    content: str


@dataclass
class AIResponse:
    content: str
    model: str
    usage: dict[str, int] | None = field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0}
    )


class AIProvider(Protocol):
    name: str

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:  # pragma: no cover
        ...


def _normalize_usage(data: dict[str, Any] | None, provider: str) -> dict[str, int]:
    if not data:
        return {"prompt_tokens": 0, "completion_tokens": 0}
    if provider == "ollama":
        return {
            "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
            "completion_tokens": int(data.get("eval_count", 0) or 0),
        }
    if provider == "anthropic":
        return {
            "prompt_tokens": int(data.get("input_tokens", 0) or 0),
            "completion_tokens": int(data.get("output_tokens", 0) or 0),
        }
    # openai style
    return {
        "prompt_tokens": int(data.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(data.get("completion_tokens", 0) or 0),
    }


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        timeout: int = 60,
        **_: Any,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", self.timeout)) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = (data.get("message") or {}).get("content", "")
        usage = _normalize_usage(data, "ollama")
        return AIResponse(content=content, model=payload["model"], usage=usage)


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        **_: Any,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", self.timeout)) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        content = ""
        if choices:
            content = ((choices[0] or {}).get("message") or {}).get("content", "") or ""
        usage = _normalize_usage(data.get("usage"), "openai")
        return AIResponse(content=content, model=payload["model"], usage=usage)


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-3-5-sonnet",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: int = 60,
        **_: Any,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        # Convert messages: Anthropic expects user/assistant roles; keep simple mapping
        mapped = [{"role": m.role, "content": m.content} for m in messages]
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": mapped,
            "max_tokens": int(kwargs.get("max_tokens", 1024)),
        }
        headers = {
            "anthropic-version": kwargs.get("anthropic_version", "2023-06-01"),
            "content-type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        async with httpx.AsyncClient(timeout=kwargs.get("timeout", self.timeout)) as client:
            resp = await client.post(f"{self.base_url}/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content_blocks = data.get("content") or []
        content = ""
        if content_blocks:
            first = content_blocks[0] or {}
            content = first.get("text", "") or ""
        usage = _normalize_usage(data.get("usage"), "anthropic")
        return AIResponse(content=content, model=payload["model"], usage=usage)


def get_provider(name: str | None = None, **kwargs) -> AIProvider:
    settings = None
    try:
        settings = get_settings()
    except Exception:
        settings = None

    provider_name = name or (getattr(settings, "ai_provider", "ollama") if settings else "ollama")
    timeout = kwargs.pop(
        "timeout", getattr(settings, "ai_request_timeout_s", 60) if settings else 60
    )

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=kwargs.pop(
                "api_key", getattr(settings, "ai_openai_api_key", "") if settings else ""
            ),
            model=kwargs.pop(
                "model",
                getattr(settings, "ai_openai_model", "gpt-4o-mini") if settings else "gpt-4o-mini",
            ),
            base_url=kwargs.pop(
                "base_url",
                getattr(settings, "ai_openai_base_url", "https://api.openai.com/v1")
                if settings
                else "https://api.openai.com/v1",
            ),
            timeout=timeout,
            **kwargs,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=kwargs.pop(
                "api_key", getattr(settings, "ai_anthropic_api_key", "") if settings else ""
            ),
            model=kwargs.pop(
                "model",
                getattr(settings, "ai_anthropic_model", "claude-3-5-sonnet")
                if settings
                else "claude-3-5-sonnet",
            ),
            base_url=kwargs.pop(
                "base_url",
                getattr(settings, "ai_anthropic_base_url", "https://api.anthropic.com/v1")
                if settings
                else "https://api.anthropic.com/v1",
            ),
            timeout=timeout,
            **kwargs,
        )
    return OllamaProvider(
        base_url=kwargs.pop(
            "base_url",
            getattr(settings, "ai_ollama_base_url", "http://localhost:11434")
            if settings
            else "http://localhost:11434",
        ),
        model=kwargs.pop(
            "model",
            getattr(settings, "ai_ollama_model", "llama3.1") if settings else "llama3.1",
        ),
        timeout=timeout,
        **kwargs,
    )
