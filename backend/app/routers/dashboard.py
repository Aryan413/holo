from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage, ChatSession, Quiz, QuizAttempt, User
from ..schemas import DashboardSummary, QuizStat, SubjectStat
from ..security import require_teacher

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_pct = QuizAttempt.score * 100.0 / QuizAttempt.total


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 1)


@router.get("/summary", response_model=DashboardSummary)
def summary(_: User = Depends(require_teacher), db: Session = Depends(get_db)):
    students = db.scalar(select(func.count()).select_from(User).where(User.role == "student"))
    sessions = db.scalar(select(func.count()).select_from(ChatSession))
    questions = db.scalar(
        select(func.count()).select_from(ChatMessage).where(ChatMessage.role == "user")
    )
    attempts = db.scalar(select(func.count()).select_from(QuizAttempt))
    avg_all = db.scalar(select(func.avg(_pct)))

    per_quiz = db.execute(
        select(Quiz.id, Quiz.title, func.count(QuizAttempt.id), func.avg(_pct))
        .outerjoin(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .group_by(Quiz.id, Quiz.title)
        .order_by(Quiz.id)
    ).all()

    top_subjects = db.execute(
        select(ChatSession.subject, func.count())
        .group_by(ChatSession.subject)
        .order_by(func.count().desc(), ChatSession.subject)
        .limit(5)
    ).all()

    return DashboardSummary(
        students=students,
        chat_sessions=sessions,
        student_questions=questions,
        quiz_attempts=attempts,
        avg_quiz_score_pct=_round(avg_all),
        quizzes=[
            QuizStat(quiz_id=i, title=t, attempts=n, avg_score_pct=_round(a))
            for i, t, n, a in per_quiz
        ],
        top_subjects=[SubjectStat(subject=s, sessions=n) for s, n in top_subjects],
    )
