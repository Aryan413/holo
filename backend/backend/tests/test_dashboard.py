from tests.test_quiz import QUIZ


def test_dashboard_is_teacher_only(client, make_user):
    student = make_user("s@example.com")
    assert client.get("/dashboard/summary", headers=student).status_code == 403
    assert client.get("/dashboard/summary").status_code == 401


def test_empty_dashboard(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    body = client.get("/dashboard/summary", headers=teacher).json()
    assert body["students"] == 0
    assert body["quiz_attempts"] == 0
    assert body["avg_quiz_score_pct"] is None
    assert body["quizzes"] == [] and body["top_subjects"] == []


def test_dashboard_counts_activity(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    s1 = make_user("s1@example.com")
    s2 = make_user("s2@example.com")

    client.post("/tutor/chat", json={"message": "a", "subject": "Physics"}, headers=s1)
    client.post("/tutor/chat", json={"message": "b", "subject": "Physics"}, headers=s2)
    client.post("/tutor/chat", json={"message": "c", "subject": "Maths"}, headers=s2)

    quiz_id = client.post("/quizzes", json=QUIZ, headers=teacher).json()["id"]
    client.post(f"/quizzes/{quiz_id}/attempts", json={"answers": [0, 1]}, headers=s1)  # 100%
    client.post(f"/quizzes/{quiz_id}/attempts", json={"answers": [1, 0]}, headers=s2)  # 0%

    body = client.get("/dashboard/summary", headers=teacher).json()
    assert body["students"] == 2  # the teacher is not counted
    assert body["chat_sessions"] == 3
    assert body["student_questions"] == 3
    assert body["quiz_attempts"] == 2
    assert body["avg_quiz_score_pct"] == 50.0
    assert body["quizzes"] == [
        {"quiz_id": quiz_id, "title": QUIZ["title"], "attempts": 2, "avg_score_pct": 50.0}
    ]
    assert body["top_subjects"][0] == {"subject": "Physics", "sessions": 2}
