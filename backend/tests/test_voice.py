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


def test_vocabulary_prompt_uses_note_titles_in_the_spoken_language(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: ["Ohm's law", "ഓമിന്റെ നിയമം", "Kirchhoff's laws"])
    assert stt.vocabulary_prompt("en") == "Topics: Ohm's law, Kirchhoff's laws."
    assert stt.vocabulary_prompt("ml") == "ഓമിന്റെ നിയമം."


def test_vocabulary_prompt_is_none_without_notes(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: [])
    assert stt.vocabulary_prompt("en") is None
    monkeypatch.setattr(stt, "list_topics", lambda: ["Ohm's law"])
    assert stt.vocabulary_prompt("ml") is None  # English titles don't help Malayalam speech


def test_vocabulary_prompt_stays_short(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: [f"Topic number {i}" for i in range(500)])
    assert len(stt.vocabulary_prompt("en")) <= stt.MAX_PROMPT_CHARS + len("Topics: .")


def test_whisper_is_given_the_vocabulary_prompt(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: ["Ohm's law"])

    class FakeModel:
        def transcribe(self, path, **options):
            self.options = options
            return [type("Segment", (), {"text": " What is Ohm's law? "})()], None

    transcriber = stt.WhisperTranscriber()
    transcriber._model = FakeModel()
    assert transcriber.transcribe(b"audio", "en") == "What is Ohm's law?"
    assert transcriber._model.options["initial_prompt"] == "Topics: Ohm's law."
    assert transcriber._model.options["language"] == "en"


def test_whisper_uses_accuracy_options(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: [])

    class FakeModel:
        def transcribe(self, path, **options):
            self.options = options
            return [], None

    transcriber = stt.WhisperTranscriber()
    transcriber._model = FakeModel()
    transcriber.transcribe(b"audio", "en")
    options = transcriber._model.options
    assert options["beam_size"] == 5
    assert options["condition_on_previous_text"] is False
    assert options["vad_filter"] is True


def test_made_up_text_over_noise_is_dropped(monkeypatch):
    monkeypatch.setattr(stt, "list_topics", lambda: [])

    def segment(text, no_speech_prob, avg_logprob):
        return type("Segment", (), {"text": text, "no_speech_prob": no_speech_prob, "avg_logprob": avg_logprob})()

    class FakeModel:
        def transcribe(self, path, **options):
            return [segment(" What is Ohm's law?", 0.05, -0.2), segment(" Thank you for watching.", 0.9, -1.4)], None

    transcriber = stt.WhisperTranscriber()
    transcriber._model = FakeModel()
    assert transcriber.transcribe(b"audio", "en") == "What is Ohm's law?"


def test_auto_picks_large_model_on_gpu(monkeypatch):
    monkeypatch.setattr(stt, "gpu_ready", lambda: True)
    assert stt.resolve_runtime("auto", "auto", "auto") == ("large-v3", "cuda", "int8_float16")


def test_auto_picks_small_model_on_cpu(monkeypatch):
    monkeypatch.setattr(stt, "gpu_ready", lambda: False)
    assert stt.resolve_runtime("auto", "auto", "auto") == ("small", "cpu", "int8")


def test_explicit_settings_are_kept(monkeypatch):
    monkeypatch.setattr(stt, "gpu_ready", lambda: True)
    assert stt.resolve_runtime("medium", "cpu", "int8") == ("medium", "cpu", "int8")


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
