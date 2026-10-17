import pytest

from app.config import settings
from app.main import app
from app.services import stt
from app.services.stt import SpeechUnavailable, get_transcriber


class FakeTranscriber:
    def __init__(self, text="what is ohm's law", error=None):
        self.text, self.error, self.calls = text, error, []

    def transcribe(self, audio, language):
        self.calls.append((audio, language))
        if self.error:
            raise self.error
        return self.text


@pytest.fixture()
def fake(client):
    fake = FakeTranscriber()
    app.dependency_overrides[get_transcriber] = lambda: fake
    yield fake


def upload(client, headers, data=b"audio-bytes", language="en"):
    return client.post(
        "/voice/transcribe",
        headers=headers,
        files={"audio": ("clip.webm", data, "audio/webm")},
        data={"language": language},
    )


def test_requires_sign_in(client, fake):
    r = client.post("/voice/transcribe", files={"audio": ("c.webm", b"x", "audio/webm")}, data={"language": "en"})
    assert r.status_code == 401
    assert fake.calls == []


def test_transcribes_audio(client, make_user, fake):
    headers = make_user("s@example.com")
    r = upload(client, headers, b"hello", "ml")
    assert r.status_code == 200
    assert r.json() == {"text": "what is ohm's law"}
    assert fake.calls == [(b"hello", "ml")]


def test_language_defaults_to_english(client, make_user, fake):
    headers = make_user("s@example.com")
    r = client.post("/voice/transcribe", headers=headers, files={"audio": ("c.webm", b"x", "audio/webm")})
    assert r.status_code == 200
    assert fake.calls[0][1] == "en"


def test_rejects_unknown_language(client, make_user, fake):
    r = upload(client, make_user("s@example.com"), language="fr")
    assert r.status_code == 422
    assert fake.calls == []


def test_rejects_empty_recording(client, make_user, fake):
    r = upload(client, make_user("s@example.com"), data=b"")
    assert r.status_code == 422
    assert fake.calls == []


def test_rejects_oversized_recording(client, make_user, fake, monkeypatch):
    monkeypatch.setattr(settings, "max_audio_mb", 1)
    r = upload(client, make_user("s@example.com"), data=b"x" * (1024 * 1024 + 1))
    assert r.status_code == 413
    assert fake.calls == []


def test_no_speech_heard(client, make_user, fake):
    fake.text = ""
    r = upload(client, make_user("s@example.com"))
    assert r.status_code == 422
    assert "couldn't hear" in r.json()["detail"]


def test_not_installed_gives_instructions(client, make_user, fake):
    fake.error = SpeechUnavailable("Voice input isn't installed. Run pip install -r requirements-voice.txt")
    r = upload(client, make_user("s@example.com"))
    assert r.status_code == 503
    assert "requirements-voice.txt" in r.json()["detail"]


def test_unexpected_failure_is_a_502_without_details(client, make_user, fake):
    fake.error = RuntimeError("secret internal path /tmp/x")
    r = upload(client, make_user("s@example.com"))
    assert r.status_code == 502
    assert "secret" not in r.json()["detail"]


def test_whisper_missing_library_raises_helpful_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_faster_whisper(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_faster_whisper)
    with pytest.raises(SpeechUnavailable, match="requirements-voice.txt"):
        stt.WhisperTranscriber().transcribe(b"x", "en")
