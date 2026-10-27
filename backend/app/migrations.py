"""Keeps the database's tables in step with the code. Table changes are Alembic migrations in
backend/migrations/versions (see backend/README.md, "Changing the tables").

At startup:
- A database made before migrations existed (tables, no version) is adopted as it is.
- A local SQLite database is brought up to date automatically.
- The shared database is never changed automatically: an unmerged branch must not alter it for
  the whole team. If it is behind or ahead of the code, the server stops and says what to do.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect

BACKEND = Path(__file__).resolve().parents[1]
BASELINE = "0001"  # the first migration: the tables as they were before migrations existed


class DatabaseOutOfStep(RuntimeError):
    """The database and the code disagree about the tables. The message says what to do."""


def alembic_config(database_url: str, connection=None) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes.update(database_url=database_url, connection=connection, configure_logger=False)
    return config


def prepare_database(engine: Engine, database_url: str, auto_upgrade: bool | None = None) -> str:
    """Checks (and for local databases updates) the tables. Returns what it did, for the log.
    auto_upgrade defaults to True for SQLite (one computer) and False for anything shared."""
    if auto_upgrade is None:
        auto_upgrade = engine.dialect.name == "sqlite"
    script = ScriptDirectory.from_config(alembic_config(database_url))
    head = script.get_current_head()
    known = {revision.revision for revision in script.walk_revisions()}

    with engine.begin() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
        adopted = False
        if current is None and inspect(connection).has_table("users"):
            # Made by the app before migrations existed: exactly the first migration's tables.
            command.stamp(alembic_config(database_url, connection), BASELINE)
            current, adopted = BASELINE, True

        if current == head:
            return "adopted, up to date" if adopted else "up to date"
        if current is not None and current not in known:
            raise DatabaseOutOfStep(
                "The database has been updated by newer code than yours. "
                "Run 'git pull' (and 'pip install -r requirements.txt'), then start the server again."
            )
        if auto_upgrade:
            command.upgrade(alembic_config(database_url, connection), "head")
            return f"updated to {head}"

    pending = [f"  {rev.revision}: {rev.doc}" for rev in reversed(list(script.iterate_revisions(head, current or "base")))]
    raise DatabaseOutOfStep(
        f"The shared database needs {len(pending)} table update(s) that this code expects:\n"
        + "\n".join(pending)
        + "\nIf they are in main, one person applies them once, from the backend folder:\n"
        "  .\\venv\\Scripts\\python.exe -m alembic upgrade head\n"
        "If they come from your own unmerged branch, try them on your local database first "
        "(DATABASE_URL=sqlite:///./holox.db in .env)."
    )
