import os

# Tests must never touch a real database, above all the team's shared one named in backend/.env.
# An environment variable wins over .env, and it has to be set before the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEACHER_CODE = "letmein"


@pytest.fixture()
def client(monkeypatch):
    """Each test gets a fresh in-memory database. No holox.db file is touched."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Testing = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = Testing()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "teacher_signup_code", TEACHER_CODE)
    monkeypatch.setattr(settings, "llm_provider", "echo")
    monkeypatch.setattr(settings, "tts_provider", "browser")  # never call ElevenLabs from tests

    # Not used as a context manager on purpose: that would run the app's startup
    # hook against the real database file.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(client):
    """Registers a user, logs in, and returns the Authorization header."""

    def _make(email, role="student", name="Test User", password="password123"):
        payload = {"email": email, "name": name, "password": password, "role": role}
        if role == "teacher":
            payload["teacher_code"] = TEACHER_CODE
        r = client.post("/auth/register", json=payload)
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
