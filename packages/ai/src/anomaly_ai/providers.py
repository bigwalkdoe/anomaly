from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AIMessage:
    role: str
    content: str


@dataclass
class AIResponse:
    content: str
    model: str
    usage: dict[str, int] = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0}


class AIProvider(Protocol):
    name: str

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:  # pragma: no cover
        ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        # Stub implementation for tests
        content = "\n".join(m.content for m in messages if m.role == "user")[-200:]
        return AIResponse(
            content=f"AI: {content}",
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        content = "\n".join(m.content for m in messages if m.role == "user")[-200:]
        return AIResponse(
            content=f"OpenAI: {content}",
            model=self.model,
            usage={"prompt_tokens": 15, "completion_tokens": 25},
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str = "", model: str = "claude-3-5-sonnet"):
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        content = "\n".join(m.content for m in messages if m.role == "user")[-200:]
        return AIResponse(
            content=f"Anthropic: {content}",
            model=self.model,
            usage={"prompt_tokens": 12, "completion_tokens": 22},
        )


def get_provider(name: str = "ollama", **kwargs) -> AIProvider:
    if name == "openai":
        return OpenAIProvider(**kwargs)
    if name == "anthropic":
        return AnthropicProvider(**kwargs)
    return OllamaProvider(**kwargs)
