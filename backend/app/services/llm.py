"""LLM providers. The tutor router only talks to the LLMProvider interface,
so swapping models or vendors means adding a class here."""

from typing import Protocol

import httpx

from ..config import settings


class LLMProvider(Protocol):
    def generate(self, system: str, messages: list[dict]) -> str:
        """messages: [{"role": "user"|"assistant", "content": str}, ...], last one is the user's."""
        ...


class EchoProvider:
    """Offline provider for development and tests. Needs no API key."""

    def generate(self, system: str, messages: list[dict]) -> str:
        last = messages[-1]["content"]
        return (
            f"[dev mode] You asked: {last}\n"
            "Set LLM_PROVIDER=anthropic and LLM_API_KEY in .env to get real tutor answers."
        )


class AnthropicProvider:
    """Calls the Anthropic Messages API over HTTPS."""

    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate(self, system: str, messages: list[dict]) -> str:
        response = httpx.post(
            self.URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1024,
                "system": system,
                "messages": messages,
            },
            timeout=60,
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


def get_provider() -> LLMProvider:
    """FastAPI dependency. Tests override this."""
    if settings.llm_provider == "anthropic":
        if not settings.llm_api_key:
            raise RuntimeError("LLM_PROVIDER=anthropic but LLM_API_KEY is empty")
        return AnthropicProvider(settings.llm_api_key, settings.llm_model)
    return EchoProvider()
