import httpx

from app.services.llm import get_provider
from app.main import app


class Recorder:
    def __init__(self, reply="ok"):
        self.reply = reply
        self.calls = []

    def generate(self, system, messages):
        self.calls.append((system, messages))
        return self.reply


class Broken:
    def generate(self, system, messages):
        raise httpx.ConnectError("no network")


def test_chat_creates_session_and_stores_both_messages(client, make_user):
    headers = make_user("s@example.com")
    r = client.post(
        "/tutor/chat",
        json={"message": "What is Ohm's law?", "subject": "Physics"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "Ohm's law" in body["reply"]  # echo provider repeats the question

    detail = client.get(f"/tutor/sessions/{body['session_id']}", headers=headers).json()
    assert detail["subject"] == "Physics"
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_follow_up_reuses_session_and_sends_history(client, make_user):
    headers = make_user("s@example.com")
    recorder = Recorder("first answer")
    app.dependency_overrides[get_provider] = lambda: recorder

    first = client.post("/tutor/chat", json={"message": "Q1"}, headers=headers).json()
    client.post(
        "/tutor/chat", json={"message": "Q2", "session_id": first["session_id"]}, headers=headers
    )

    _, messages = recorder.calls[1]
    assert [m["content"] for m in messages] == ["Q1", "first answer", "Q2"]
    detail = client.get(f"/tutor/sessions/{first['session_id']}", headers=headers).json()
    assert len(detail["messages"]) == 4


def test_malayalam_is_requested_in_system_prompt(client, make_user):
    headers = make_user("s@example.com")
    recorder = Recorder()
    app.dependency_overrides[get_provider] = lambda: recorder

    client.post("/tutor/chat", json={"message": "hi", "language": "ml"}, headers=headers)
    system, _ = recorder.calls[0]
    assert "Malayalam" in system


def test_invalid_language_rejected(client, make_user):
    headers = make_user("s@example.com")
    r = client.post("/tutor/chat", json={"message": "hi", "language": "fr"}, headers=headers)
    assert r.status_code == 422


def test_sessions_are_private_to_their_owner(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    sid = client.post("/tutor/chat", json={"message": "secret"}, headers=alice).json()["session_id"]

    assert client.get(f"/tutor/sessions/{sid}", headers=bob).status_code == 404
    r = client.post("/tutor/chat", json={"message": "hi", "session_id": sid}, headers=bob)
    assert r.status_code == 404
    assert client.get("/tutor/sessions", headers=bob).json() == []
    assert len(client.get("/tutor/sessions", headers=alice).json()) == 1


def test_chat_requires_login(client):
    assert client.post("/tutor/chat", json={"message": "hi"}).status_code == 401


def test_ai_failure_returns_502_and_saves_nothing(client, make_user):
    headers = make_user("s@example.com")
    app.dependency_overrides[get_provider] = lambda: Broken()

    r = client.post("/tutor/chat", json={"message": "hi"}, headers=headers)
    assert r.status_code == 502
    assert client.get("/tutor/sessions", headers=headers).json() == []
