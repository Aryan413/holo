import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.services.llm import (
    AnthropicProvider,
    EchoProvider,
    OpenAICompatibleProvider,
    get_provider,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def fake_post(response_json, calls):
    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(response_json)

    return post


# ---------- request / response shape ----------
def test_openai_compatible_request_and_parsing(monkeypatch):
    calls = []
    reply = {"choices": [{"message": {"content": "  Hello student  "}}]}
    monkeypatch.setattr("app.services.llm.httpx.post", fake_post(reply, calls))

    provider = OpenAICompatibleProvider("http://localhost:11434/v1/", "llama3.2", timeout=5)
    out = provider.generate("be kind", [{"role": "user", "content": "hi"}])

    assert out == "Hello student"
    call = calls[0]
    assert call["url"] == "http://localhost:11434/v1/chat/completions"
    assert call["json"]["model"] == "llama3.2"
    assert call["json"]["messages"] == [
        {"role": "system", "content": "be kind"},
        {"role": "user", "content": "hi"},
    ]
    assert "authorization" not in call["headers"]
    assert call["timeout"] == 5


def test_openai_compatible_sends_key_when_given(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.llm.httpx.post", fake_post({"choices": [{"message": {"content": "x"}}]}, calls)
    )
    OpenAICompatibleProvider("http://h/v1", "m", api_key="sk-test").generate(
        "s", [{"role": "user", "content": "q"}]
    )
    assert calls[0]["headers"]["authorization"] == "Bearer sk-test"


def test_openai_compatible_handles_empty_choices(monkeypatch):
    monkeypatch.setattr("app.services.llm.httpx.post", fake_post({"choices": []}, []))
    out = OpenAICompatibleProvider("http://h/v1", "m").generate("s", [{"role": "user", "content": "q"}])
    assert out == ""


def test_anthropic_request_and_parsing(monkeypatch):
    calls = []
    reply = {"content": [{"type": "text", "text": "Hi "}, {"type": "text", "text": "there"}]}
    monkeypatch.setattr("app.services.llm.httpx.post", fake_post(reply, calls))

    out = AnthropicProvider("key-123", "some-model", timeout=7).generate(
        "be kind", [{"role": "user", "content": "hi"}]
    )

    assert out == "Hi there"
    call = calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "key-123"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["json"]["model"] == "some-model"
    assert call["json"]["system"] == "be kind"
    assert call["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert call["timeout"] == 7


# ---------- choosing a provider from settings ----------
@pytest.mark.parametrize(
    "name, base_url",
    [("ollama", "http://localhost:11434/v1"), ("lmstudio", "http://localhost:1234/v1")],
)
def test_local_providers_use_their_default_address(monkeypatch, name, base_url):
    monkeypatch.setattr(settings, "llm_provider", name)
    monkeypatch.setattr(settings, "llm_model", "my-model")
    monkeypatch.setattr(settings, "llm_base_url", "")
    provider = get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == base_url
    assert provider.model == "my-model"


def test_openai_compatible_uses_custom_address(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai_compatible")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_base_url", "http://192.168.1.5:8000/v1")
    assert get_provider().base_url == "http://192.168.1.5:8000/v1"


def test_anthropic_defaults_the_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_model", "")
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-sonnet-5-5"


def test_echo_is_the_default(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "echo")
    assert isinstance(get_provider(), EchoProvider)


# ---------- settings validation: mistakes should fail at startup with a clear message ----------
def make_settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"llm_provider": "bogus"}, "LLM_PROVIDER must be one of"),
        ({"llm_provider": "anthropic"}, "LLM_API_KEY"),
        ({"llm_provider": "ollama"}, "LLM_MODEL"),
        ({"llm_provider": "lmstudio"}, "LLM_MODEL"),
        ({"llm_provider": "openai_compatible", "llm_model": "m"}, "LLM_BASE_URL"),
    ],
)
def test_bad_llm_settings_are_rejected(kwargs, message):
    with pytest.raises(ValidationError, match=message):
        make_settings(**kwargs)


def test_good_llm_settings_are_accepted():
    make_settings()  # echo
    make_settings(llm_provider="ollama", llm_model="llama3.2")
    make_settings(llm_provider="lmstudio", llm_model="some-model")
    make_settings(llm_provider="anthropic", llm_api_key="k")
    make_settings(llm_provider="openai_compatible", llm_model="m", llm_base_url="http://h/v1")
