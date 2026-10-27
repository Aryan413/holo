"""How Alembic reaches the database: the same DATABASE_URL (backend/.env) and connection settings
as the app. Run from backend/, e.g.  python -m alembic upgrade head  (see backend/README.md)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import settings
from app.database import Base, engine_options, engine_url

config = context.config
target_metadata = Base.metadata

# From the command line, use alembic.ini's log settings. When the app calls Alembic at startup it
# passes configure_logger=False, so the server's own logging is left alone.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


def database_url() -> str:
    return config.attributes.get("database_url") or settings.database_url


def configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,  # notice column type changes too, not only new/removed columns
        render_as_batch=database_url().startswith("sqlite"),  # SQLite needs table copies to alter columns
        **kwargs,
    )


def run_migrations_offline() -> None:
    """--sql mode: print the SQL instead of running it (to review a migration)."""
    configure(url=engine_url(database_url()), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")  # given by the app at startup
    if connection is not None:
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    url = database_url()
    engine = create_engine(engine_url(url), **engine_options(url))
    with engine.connect() as connection:
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
