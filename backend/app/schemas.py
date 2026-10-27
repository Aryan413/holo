from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ---------- auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["student", "teacher"] = "student"
    teacher_code: str | None = None

    @field_validator("password")
    @classmethod
    def _bcrypt_byte_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- tutor ----------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    subject: str = Field(default="General", min_length=1, max_length=120)
    language: Literal["en", "ml"] = "en"  # English / Malayalam
    session_id: int | None = None


class ChatResponse(BaseModel):
    session_id: int
    reply: str
    # A picture to show with the answer, e.g. {"kind": "solar_system", "view": "planet", "focus": ["mars"]}
    visual: dict | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
    visual: dict | None = None  # on the tutor's answers, as in ChatResponse


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    language: str
    created_at: datetime


class SessionDetail(SessionOut):
    messages: list[MessageOut]


# ---------- voice ----------
class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)  # upper limit is MAX_SPEECH_CHARS, checked in the router
    language: Literal["en", "ml"] = "en"
    # The text read just before and after this piece. Not spoken; it keeps the tone and
    # pacing the same across pieces so the joins don't sound like a new recording.
    previous_text: str = Field(default="", max_length=1000)
    next_text: str = Field(default="", max_length=1000)


# ---------- quizzes ----------
class QuestionCreate(BaseModel):
    text: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)

    @model_validator(mode="after")
    def _index_in_range(self):
        if self.correct_index >= len(self.options):
            raise ValueError("correct_index must point at one of the options")
        return self


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(default="", max_length=120)
    questions: list[QuestionCreate] = Field(min_length=1, max_length=100)


class QuestionOut(BaseModel):
    id: int
    text: str
    options: list[str]
    correct_index: int | None = None  # only included for teachers


class QuizOut(BaseModel):
    id: int
    title: str
    subject: str
    topic: str
    questions: list[QuestionOut]


class QuizSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subject: str
    topic: str


class AttemptCreate(BaseModel):
    answers: list[int]


class AttemptOut(BaseModel):
    score: int
    total: int
    correct: list[bool]


# ---------- dashboard ----------
class QuizStat(BaseModel):
    quiz_id: int
    title: str
    attempts: int
    avg_score_pct: float | None


class SubjectStat(BaseModel):
    subject: str
    sessions: int


class DashboardSummary(BaseModel):
    students: int
    chat_sessions: int
    student_questions: int
    quiz_attempts: int
    avg_quiz_score_pct: float | None
    quizzes: list[QuizStat]
    top_subjects: list[SubjectStat]
