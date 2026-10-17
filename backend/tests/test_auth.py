def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_login_me(client, make_user):
    headers = make_user("Asha@Example.com", name="Asha")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "asha@example.com"  # stored lower-case
    assert body["role"] == "student"
    assert "password" not in body and "hashed_password" not in body


def test_duplicate_email_rejected(client, make_user):
    make_user("a@example.com")
    r = client.post(
        "/auth/register",
        json={"email": "A@example.com", "name": "Again", "password": "password123"},
    )
    assert r.status_code == 409


def test_wrong_password_rejected(client, make_user):
    make_user("a@example.com")
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "nope-nope"})
    assert r.status_code == 401


def test_unknown_user_rejected(client):
    r = client.post("/auth/login", data={"username": "ghost@example.com", "password": "password123"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post(
        "/auth/register", json={"email": "a@example.com", "name": "A", "password": "short"}
    )
    assert r.status_code == 422


def test_teacher_signup_needs_correct_code(client):
    base = {"email": "t@example.com", "name": "T", "password": "password123", "role": "teacher"}
    assert client.post("/auth/register", json=base).status_code == 403
    assert client.post("/auth/register", json={**base, "teacher_code": "wrong"}).status_code == 403
    assert client.post("/auth/register", json={**base, "teacher_code": "letmein"}).status_code == 201


def test_teacher_signup_disabled_when_no_code_configured(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "teacher_signup_code", "")
    r = client.post(
        "/auth/register",
        json={
            "email": "t@example.com",
            "name": "T",
            "password": "password123",
            "role": "teacher",
            "teacher_code": "",
        },
    )
    assert r.status_code == 403


def test_protected_routes_need_a_token(client):
    assert client.get("/auth/me").status_code == 401
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
