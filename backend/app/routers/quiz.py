from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Question, Quiz, QuizAttempt, User
from ..schemas import (
    AttemptCreate,
    AttemptOut,
    QuestionOut,
    QuizCreate,
    QuizOut,
    QuizSummary,
)
from ..security import get_current_user, require_teacher

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _quiz_out(quiz: Quiz, reveal_answers: bool) -> QuizOut:
    """Students never receive correct_index; it is None and dropped from the response."""
    return QuizOut(
        id=quiz.id,
        title=quiz.title,
        subject=quiz.subject,
        topic=quiz.topic,
        questions=[
            QuestionOut(
                id=q.id,
                text=q.text,
                options=q.options,
                correct_index=q.correct_index if reveal_answers else None,
            )
            for q in quiz.questions
        ],
    )


@router.post(
    "",
    response_model=QuizOut,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz(
    body: QuizCreate, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    quiz = Quiz(
        title=body.title,
        subject=body.subject,
        topic=body.topic,
        created_by=teacher.id,
        questions=[
            Question(text=q.text, options=q.options, correct_index=q.correct_index)
            for q in body.questions
        ],
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return _quiz_out(quiz, reveal_answers=True)


@router.get("", response_model=list[QuizSummary])
def list_quizzes(
    subject: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Quiz).order_by(Quiz.id.desc())
    if subject:
        stmt = stmt.where(Quiz.subject == subject)
    return db.scalars(stmt).all()


@router.get("/{quiz_id}", response_model=QuizOut, response_model_exclude_none=True)
def get_quiz(
    quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    return _quiz_out(quiz, reveal_answers=user.role == "teacher")


@router.post(
    "/{quiz_id}/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED
)
def submit_attempt(
    quiz_id: int,
    body: AttemptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    if len(body.answers) != len(quiz.questions):
        raise HTTPException(422, "Provide exactly one answer per question")

    correct = [a == q.correct_index for a, q in zip(body.answers, quiz.questions)]
    attempt = QuizAttempt(
        quiz_id=quiz.id, user_id=user.id, score=sum(correct), total=len(correct)
    )
    db.add(attempt)
    db.commit()
    return AttemptOut(score=attempt.score, total=attempt.total, correct=correct)
