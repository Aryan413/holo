QUIZ = {
    "title": "Ohm's law basics",
    "subject": "Physics",
    "topic": "Circuits",
    "questions": [
        {"text": "V = ?", "options": ["I*R", "I/R", "R/I"], "correct_index": 0},
        {"text": "Unit of resistance?", "options": ["Volt", "Ohm"], "correct_index": 1},
    ],
}


def test_teacher_creates_quiz_and_sees_answers(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    r = client.post("/quizzes", json=QUIZ, headers=teacher)
    assert r.status_code == 201
    assert [q["correct_index"] for q in r.json()["questions"]] == [0, 1]


def test_student_cannot_create_quiz(client, make_user):
    student = make_user("s@example.com")
    assert client.post("/quizzes", json=QUIZ, headers=student).status_code == 403


def test_students_never_see_correct_answers(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    student = make_user("s@example.com")
    quiz_id = client.post("/quizzes", json=QUIZ, headers=teacher).json()["id"]

    body = client.get(f"/quizzes/{quiz_id}", headers=student).json()
    assert len(body["questions"]) == 2
    assert all("correct_index" not in q for q in body["questions"])

    as_teacher = client.get(f"/quizzes/{quiz_id}", headers=teacher).json()
    assert all("correct_index" in q for q in as_teacher["questions"])


def test_attempt_is_scored(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    student = make_user("s@example.com")
    quiz_id = client.post("/quizzes", json=QUIZ, headers=teacher).json()["id"]

    r = client.post(f"/quizzes/{quiz_id}/attempts", json={"answers": [0, 0]}, headers=student)
    assert r.status_code == 201
    assert r.json() == {"score": 1, "total": 2, "correct": [True, False]}


def test_attempt_needs_one_answer_per_question(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    student = make_user("s@example.com")
    quiz_id = client.post("/quizzes", json=QUIZ, headers=teacher).json()["id"]

    r = client.post(f"/quizzes/{quiz_id}/attempts", json={"answers": [0]}, headers=student)
    assert r.status_code == 422


def test_invalid_quiz_payloads_rejected(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    out_of_range = {**QUIZ, "questions": [{"text": "Q", "options": ["a", "b"], "correct_index": 5}]}
    one_option = {**QUIZ, "questions": [{"text": "Q", "options": ["a"], "correct_index": 0}]}
    no_questions = {**QUIZ, "questions": []}
    for bad in (out_of_range, one_option, no_questions):
        assert client.post("/quizzes", json=bad, headers=teacher).status_code == 422


def test_missing_quiz_is_404(client, make_user):
    student = make_user("s@example.com")
    assert client.get("/quizzes/999", headers=student).status_code == 404
    r = client.post("/quizzes/999/attempts", json={"answers": []}, headers=student)
    assert r.status_code == 404


def test_list_quizzes_filters_by_subject(client, make_user):
    teacher = make_user("t@example.com", role="teacher")
    client.post("/quizzes", json=QUIZ, headers=teacher)
    client.post("/quizzes", json={**QUIZ, "title": "Maths", "subject": "Maths"}, headers=teacher)

    assert len(client.get("/quizzes", headers=teacher).json()) == 2
    physics = client.get("/quizzes", params={"subject": "Physics"}, headers=teacher).json()
    assert [q["title"] for q in physics] == ["Ohm's law basics"]
