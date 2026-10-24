import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app
from app.services import tts
from app.services.tts import ElevenLabsSpeaker, VoiceUnavailable, get_speaker


class FakeSpeaker:
    def __init__(self, audio=b"ID3-mp3-bytes", error=None):
        self.audio, self.error, self.calls = audio, error, []

    def synthesize(self, text, language, previous_text="", next_text=""):
        self.calls.append((text, language))
        self.context = (previous_text, next_text)
        if self.error:
            raise self.error
        return self.audio


@pytest.fixture()
def fake(client):
    fake = FakeSpeaker()
    app.dependency_overrides[get_speaker] = lambda: fake
    yield fake


def speak(client, headers, text="Ohm's law says V = IR.", language="en"):
    return client.post("/voice/speak", headers=headers, json={"text": text, "language": language})


# ---------- /voice/options ----------
def test_options_say_browser_by_default(client, make_user):
    r = client.get("/voice/options", headers=make_user("s@example.com"))
    assert r.json() == {"speech": "browser"}


def test_options_say_elevenlabs_when_turned_on(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "tts_provider", "elevenlabs")
    r = client.get("/voice/options", headers=make_user("s@example.com"))
    assert r.json() == {"speech": "elevenlabs"}


def test_options_require_sign_in(client):
    assert client.get("/voice/options").status_code == 401


# ---------- /voice/speak ----------
def test_speak_requires_sign_in(client, fake):
    r = client.post("/voice/speak", json={"text": "hi", "language": "en"})
    assert r.status_code == 401
    assert fake.calls == []  # nobody can spend the voice allowance without an account


def test_speak_returns_mp3(client, make_user, fake):
    r = speak(client, make_user("s@example.com"), "  നമസ്കാരം  ", "ml")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3-mp3-bytes"
    assert fake.calls == [("നമസ്കാരം", "ml")]


def test_speak_passes_the_surrounding_text_for_smooth_joins(client, make_user, fake):
    r = client.post("/voice/speak", headers=make_user("s@example.com"), json={
        "text": "Current is the flow of charge.", "language": "en",
        "previous_text": " Voltage pushes charge. ", "next_text": "Resistance slows it.",
    })
    assert r.status_code == 200
    assert fake.context == ("Voltage pushes charge.", "Resistance slows it.")


def test_speak_context_is_optional(client, make_user, fake):
    assert speak(client, make_user("s@example.com")).status_code == 200
    assert fake.context == ("", "")


def test_speak_rejects_huge_context(client, make_user, fake):
    r = client.post("/voice/speak", headers=make_user("s@example.com"),
                    json={"text": "hi", "language": "en", "previous_text": "x" * 1001})
    assert r.status_code == 422
    assert fake.calls == []


def test_speak_rejects_unknown_language(client, make_user, fake):
    assert speak(client, make_user("s@example.com"), language="fr").status_code == 422
    assert fake.calls == []


def test_speak_rejects_blank_text(client, make_user, fake):
    assert speak(client, make_user("s@example.com"), text="   ").status_code == 422
    assert fake.calls == []


def test_speak_rejects_too_long_text(client, make_user, fake, monkeypatch):
    monkeypatch.setattr(settings, "max_speech_chars", 10)
    r = speak(client, make_user("s@example.com"), text="x" * 11)
    assert r.status_code == 413
    assert fake.calls == []


def test_speak_without_a_voice_service_is_503(client, make_user):
    app.dependency_overrides[get_speaker] = lambda: None
    assert speak(client, make_user("s@example.com")).status_code == 503


def test_voice_service_problem_is_503_with_its_message(client, make_user, fake):
    fake.error = VoiceUnavailable("this month's voice allowance is used up.")
    r = speak(client, make_user("s@example.com"))
    assert r.status_code == 503
    assert "allowance" in r.json()["detail"]


def test_unexpected_failure_is_a_502_without_details(client, make_user, fake):
    fake.error = RuntimeError("secret key sk-123")
    r = speak(client, make_user("s@example.com"))
    assert r.status_code == 502
    assert "secret" not in r.json()["detail"]


# ---------- the ElevenLabs request ----------
class FakeResponse:
    def __init__(self, status_code=200, content=b"mp3", text=""):
        self.status_code, self.content, self.text = status_code, content, text


def capture_post(monkeypatch, response):
    calls = []

    def post(url, params=None, headers=None, json=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers, "json": json, "timeout": timeout})
        return response

    monkeypatch.setattr("app.services.tts.httpx.post", post)
    return calls


def test_elevenlabs_request_shape(monkeypatch):
    calls = capture_post(monkeypatch, FakeResponse(content=b"audio"))
    out = ElevenLabsSpeaker("key-123", "Voice42", "eleven_v4", timeout=7).synthesize("Hello", "ml")
    assert out == b"audio"
    call = calls[0]
    assert call["url"] == "https://api.elevenlabs.io/v1/text-to-speech/Voice42"
    assert call["params"] == {"output_format": "mp3_44100_128"}
    assert call["headers"]["xi-api-key"] == "key-123"
    assert call["json"] == {"text": "Hello", "model_id": "eleven_v4", "language_code": "ml"}
    assert call["timeout"] == 7


def test_elevenlabs_is_sent_context_only_when_given(monkeypatch):
    calls = capture_post(monkeypatch, FakeResponse())
    speaker = ElevenLabsSpeaker("k", "v", "eleven_v4")
    speaker.synthesize("Middle.", "en", previous_text="Before.", next_text="After.")
    assert calls[0]["json"]["previous_text"] == "Before."
    assert calls[0]["json"]["next_text"] == "After."
    speaker.synthesize("Alone.", "en")
    assert "previous_text" not in calls[1]["json"] and "next_text" not in calls[1]["json"]


def test_multilingual_v2_is_not_sent_a_language_code(monkeypatch):
    calls = capture_post(monkeypatch, FakeResponse())
    ElevenLabsSpeaker("k", "v", "eleven_multilingual_v2").synthesize("Hello", "en")
    assert "language_code" not in calls[0]["json"]


@pytest.mark.parametrize(
    "status, words",
    [(401, "set up correctly"), (403, "set up correctly"), (429, "allowance"), (500, "couldn't read")],
)
def test_elevenlabs_errors_become_friendly_messages(monkeypatch, status, words):
    capture_post(monkeypatch, FakeResponse(status_code=status, text="detail from elevenlabs"))
    with pytest.raises(VoiceUnavailable, match=words) as info:
        ElevenLabsSpeaker("k", "v", "eleven_v4").synthesize("Hello", "en")
    assert "elevenlabs" not in str(info.value)  # their raw error stays in the server log


def test_elevenlabs_unreachable(monkeypatch):
    def post(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr("app.services.tts.httpx.post", post)
    with pytest.raises(VoiceUnavailable, match="internet"):
        ElevenLabsSpeaker("k", "v", "eleven_v4").synthesize("Hello", "en")


def test_empty_audio_is_an_error(monkeypatch):
    capture_post(monkeypatch, FakeResponse(content=b""))
    with pytest.raises(VoiceUnavailable):
        ElevenLabsSpeaker("k", "v", "eleven_v4").synthesize("Hello", "en")


# ---------- settings ----------
def test_get_speaker_follows_the_setting(monkeypatch):
    monkeypatch.setattr(settings, "tts_provider", "browser")
    assert get_speaker() is None
    monkeypatch.setattr(settings, "tts_provider", "elevenlabs")
    monkeypatch.setattr(settings, "elevenlabs_api_key", "k")
    assert isinstance(get_speaker(), tts.ElevenLabsSpeaker)


def test_elevenlabs_needs_a_key():
    with pytest.raises(ValidationError, match="ELEVENLABS_API_KEY"):
        Settings(tts_provider="elevenlabs", elevenlabs_api_key="")


def test_unknown_tts_provider_is_refused():
    with pytest.raises(ValidationError, match="TTS_PROVIDER"):
        Settings(tts_provider="robot")


@pytest.mark.parametrize("voice_id", ["../../v1/user", "George voice", "a/b", ""])
def test_voice_id_must_be_an_id(voice_id):
    with pytest.raises(ValidationError, match="ELEVENLABS_VOICE_ID"):
        Settings(elevenlabs_voice_id=voice_id)
