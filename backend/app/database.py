from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def engine_url(url: str) -> str:
    """Accept a connection string exactly as Neon or Supabase show it ("postgresql://..." or
    "postgres://..."). SQLAlchemy would otherwise look for the older psycopg2 driver."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # A shared cloud database closes idle connections (Neon sleeps after a few minutes):
    # test each one before use and replace it after 5 minutes, instead of failing a request.
    options = {"pool_pre_ping": True, "pool_recycle": 300}
    if "-pooler" in url:
        # Neon's pooled address (PgBouncer) can't keep the prepared statements psycopg makes
        # for repeated queries; without this they fail at random under load.
        options["connect_args"] = {"prepare_threshold": None}
    return options


engine = create_engine(engine_url(settings.database_url), **engine_options(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
