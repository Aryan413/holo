import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.database import Base
from app.migrations import BASELINE, DatabaseOutOfStep, alembic_config, prepare_database
from app.models import User


def database(tmp_path, name="app.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    return create_engine(url), url


def version(engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def head(url):
    return ScriptDirectory.from_config(alembic_config(url)).get_current_head()


def test_migrations_build_exactly_the_tables_in_the_models(tmp_path):
    engine, url = database(tmp_path)
    with engine.begin() as connection:
        command.upgrade(alembic_config(url, connection), "head")
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []  # a model change without a migration would show up here


def test_the_first_migration_is_the_baseline(tmp_path):
    _, url = database(tmp_path)
    script = ScriptDirectory.from_config(alembic_config(url))
    assert script.get_base() == BASELINE


def test_a_new_local_database_is_built_automatically(tmp_path):
    engine, url = database(tmp_path)
    assert prepare_database(engine, url).startswith("updated")
    assert {"users", "chat_sessions", "quizzes"} <= set(inspect(engine).get_table_names())
    assert version(engine) == head(url)
    assert prepare_database(engine, url) == "up to date"


def test_a_database_from_before_migrations_is_adopted_with_its_data(tmp_path):
    engine, url = database(tmp_path)
    Base.metadata.create_all(engine)  # how the app made tables before migrations
    with Session(engine) as db:
        db.add(User(email="a@school.edu", name="A", hashed_password="x"))
        db.commit()

    assert prepare_database(engine, url, auto_upgrade=False).startswith("adopted")
    assert version(engine) == head(url)
    with engine.connect() as connection:
        assert connection.execute(text("select email from users")).scalar() == "a@school.edu"


def test_the_shared_database_is_never_changed_automatically(tmp_path):
    engine, url = database(tmp_path)
    with pytest.raises(DatabaseOutOfStep, match="alembic upgrade head") as problem:
        prepare_database(engine, url, auto_upgrade=False)
    assert "0001: initial tables" in str(problem.value)
    assert inspect(engine).get_table_names() == []  # nothing was created


def test_a_database_newer_than_the_code_says_to_pull(tmp_path):
    engine, url = database(tmp_path)
    prepare_database(engine, url)
    with engine.begin() as connection:
        connection.execute(text("update alembic_version set version_num = 'f00dcafe1234'"))
    with pytest.raises(DatabaseOutOfStep, match="git pull"):
        prepare_database(engine, url)

