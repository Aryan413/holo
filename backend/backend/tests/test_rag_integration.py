import pytest

pytest.importorskip("holox_ai")

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.llm import get_provider  # noqa: E402


class Recorder:
    def __init__(self):
        self.calls = []

    def generate(self, system, messages):
        self.calls.append((system, messages))
        return "ok"


def _write_note(folder):
    (folder / "Physics").mkdir()
    (folder / "Physics" / "ohm.md").write_text(
        "# Ohm's law\n\nVoltage equals current times resistance.\n", encoding="utf-8"
    )


def test_matching_notes_reach_the_llm(client, make_user, tmp_path, monkeypatch):
    _write_note(tmp_path)
    monkeypatch.setattr(settings, "notes_dir", str(tmp_path))
    recorder = Recorder()
    app.dependency_overrides[get_provider] = lambda: recorder
    headers = make_user("s@example.com")

    r = client.post(
        "/tutor/chat",
        json={"message": "What is Ohm's law?", "subject": "Physics"},
        headers=headers,
    )
    assert r.status_code == 200
    system, _ = recorder.calls[0]
    assert "Voltage equals current times resistance" in system
    assert "Physics/ohm.md" in system


def test_question_with_no_matching_notes_adds_no_reference_section(
    client, make_user, tmp_path, monkeypatch
):
    _write_note(tmp_path)
    monkeypatch.setattr(settings, "notes_dir", str(tmp_path))
    recorder = Recorder()
    app.dependency_overrides[get_provider] = lambda: recorder
    headers = make_user("s@example.com")

    client.post("/tutor/chat", json={"message": "Explain photosynthesis"}, headers=headers)
    system, _ = recorder.calls[0]
    assert "Reference notes" not in system


def test_a_broken_engine_does_not_break_the_chat(client, make_user, monkeypatch):
    def boom(_notes_dir=None):
        raise RuntimeError("index exploded")

    monkeypatch.setattr("app.services.rag.get_retriever", boom)
    headers = make_user("s@example.com")

    r = client.post("/tutor/chat", json={"message": "hello"}, headers=headers)
    assert r.status_code == 200


def test_chat_still_works_when_engine_is_not_installed(client, make_user, monkeypatch):
    monkeypatch.setattr("app.services.rag.get_retriever", None)
    headers = make_user("s@example.com")

    r = client.post("/tutor/chat", json={"message": "hello"}, headers=headers)
    assert r.status_code == 200
