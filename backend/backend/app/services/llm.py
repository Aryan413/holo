"""LLM providers. The tutor router only talks to the LLMProvider interface,
so swapping models or vendors means adding a class here."""

from typing import Protocol

import httpx

from ..config import LOCAL_BASE_URLS, settings


class LLMProvider(Protocol):
    def generate(self, system: str, messages: list[dict]) -> str:
        """messages: [{"role": "user"|"assistant", "content": str}, ...], last one is the user's."""
        ...


class EchoProvider:
    """Offline placeholder for development and tests. It does NOT answer questions."""

    def generate(self, system: str, messages: list[dict]) -> str:
        last = messages[-1]["content"]
        return (
            f"[dev mode] You asked: {last}\n"
            "This is only a placeholder. Set LLM_PROVIDER in .env (ollama, lmstudio or "
            "anthropic) to get real tutor answers."
        )


class AnthropicProvider:
    """Calls the Anthropic Messages API over HTTPS."""

    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str, timeout: float = 120):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

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
            timeout=self.timeout,
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


class OpenAICompatibleProvider:
    """Any server that speaks the OpenAI chat API: Ollama, LM Studio, vLLM, and others."""

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, system: str, messages: list[dict]) -> str:
        headers = {"content-type": "application/json"}
        if self.api_key:  # local servers don't need one
            headers["authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "max_tokens": 1024,
                "messages": [{"role": "system", "content": system}, *messages],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        choices = response.json().get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message", {}).get("content") or "").strip()


def get_provider() -> LLMProvider:
    """FastAPI dependency. Tests override this."""
    provider = settings.llm_provider
    if provider == "anthropic":
        return AnthropicProvider(
            settings.llm_api_key,
            settings.llm_model or "claude-sonnet-5-5",
            settings.llm_timeout_seconds,
        )
    if provider in LOCAL_BASE_URLS or provider == "openai_compatible":
        return OpenAICompatibleProvider(
            settings.llm_base_url or LOCAL_BASE_URLS.get(provider, ""),
            settings.llm_model,
            settings.llm_api_key,
            settings.llm_timeout_seconds,
        )
    return EchoProvider()
