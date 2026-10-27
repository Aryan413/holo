import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import ChatMessage, ChatSession, Question, Quiz, QuizAttempt, User
from scripts.copy_to_shared_db import copy_database


def make_source(path):
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        teacher = User(email="t@school.edu", name="Teacher", hashed_password="x", role="teacher")
        student = User(email="s@school.edu", name="Student", hashed_password="y")
        tester = User(email="tester@example.com", name="Test", hashed_password="z")
        db.add_all([teacher, student, tester])
        db.flush()
        chat = ChatSession(user_id=student.id, subject="Physics", language="en")
        test_chat = ChatSession(user_id=tester.id, subject="Maths", language="en")
        db.add_all([chat, test_chat])
        db.flush()
        db.add(ChatMessage(session_id=test_chat.id, role="user", content="test question"))
        db.add_all([ChatMessage(session_id=chat.id, role="user", content="What is Ohm's law?"),
                    ChatMessage(session_id=chat.id, role="assistant", content="V = IR")])
        quiz = Quiz(title="Circuits", subject="Physics", created_by=teacher.id)
        db.add(quiz)
        db.flush()
        db.add(Question(quiz_id=quiz.id, text="V = ?", options=["IR", "I/R"], correct_index=0))
        db.add(QuizAttempt(quiz_id=quiz.id, user_id=student.id, score=1, total=1))
        db.commit()
    engine.dispose()
    return url


def test_copies_every_table_with_ids_and_links_intact(tmp_path):
    source = make_source(tmp_path / "local.db")
    target = f"sqlite:///{tmp_path / 'shared.db'}"

    counts = copy_database(source, target)

    assert counts == {"users": 2, "chat_sessions": 1, "quizzes": 1, "chat_messages": 2, "questions": 1, "quiz_attempts": 1}
    with Session(create_engine(target)) as db:
        student = db.scalar(select(User).where(User.email == "s@school.edu"))
        chat = db.scalar(select(ChatSession))
        assert chat.user_id == student.id
        assert [m.content for m in chat.messages] == ["What is Ohm's law?", "V = IR"]
        assert db.scalar(select(Question)).options == ["IR", "I/R"]


def test_refuses_to_copy_into_a_database_that_has_data(tmp_path):
    source = make_source(tmp_path / "local.db")
    target = f"sqlite:///{tmp_path / 'shared.db'}"
    copy_database(source, target)
    with pytest.raises(SystemExit, match="already has data"):
        copy_database(source, target)


def test_refuses_to_copy_a_database_onto_itself(tmp_path):
    source = make_source(tmp_path / "local.db")
    with pytest.raises(SystemExit, match="same"):
        copy_database(source, source)


def test_test_accounts_and_their_chats_are_left_behind_unless_asked(tmp_path):
    source = make_source(tmp_path / "local.db")
    counts = copy_database(source, f"sqlite:///{tmp_path / 'a.db'}")
    assert counts["users"] == 2 and counts["chat_sessions"] == 1 and counts["chat_messages"] == 2
    with Session(create_engine(f"sqlite:///{tmp_path / 'a.db'}")) as db:
        assert db.scalar(select(User).where(User.email.like("%@example.com"))) is None

    counts = copy_database(source, f"sqlite:///{tmp_path / 'b.db'}", skip_test_accounts=False)
    assert counts["users"] == 3 and counts["chat_sessions"] == 2 and counts["chat_messages"] == 3
