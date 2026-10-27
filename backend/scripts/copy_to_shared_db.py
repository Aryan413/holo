"""Copies everything from a local SQLite database (holox.db) into the shared database named by
DATABASE_URL in backend/.env: accounts, chats, quizzes and quiz results. One person runs it once,
right after creating the shared database:

    cd backend
    python -m scripts.copy_to_shared_db                  # copies ./holox.db
    python -m scripts.copy_to_shared_db --source other.db

It refuses to run if the shared database already holds data, so it can never make duplicates.
Test accounts (emails at example.com, a domain reserved for examples) and everything they own are
left behind; add --keep-example-accounts to copy them too.
The connection string (with its password) is read from .env and never printed.
"""

import argparse

from sqlalchemy import create_engine, func, inspect, select, text

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import settings
from app.database import Base, engine_options, engine_url
from app.migrations import prepare_database


TEST_DOMAIN = "@example.com"


def copy_database(source_url: str, target_url: str, skip_test_accounts: bool = True) -> dict[str, int]:
    """Copies every table, parents before children. Returns the number of rows copied per table."""
    if engine_url(source_url) == engine_url(target_url):
        raise SystemExit("The source and the shared database are the same. Nothing was copied.")
    source = create_engine(engine_url(source_url), **engine_options(source_url))
    target = create_engine(engine_url(target_url), **engine_options(target_url))
    tables = Base.metadata.sorted_tables
    # Build (or check) the tables the way every database gets them: through the migrations.
    prepare_database(target, target_url, auto_upgrade=True)

    with target.connect() as conn:
        filled = [t.name for t in tables if conn.scalar(select(func.count()).select_from(t))]
    if filled:
        raise SystemExit(f"The shared database already has data ({', '.join(filled)}). Nothing was copied.")

    existing = set(inspect(source).get_table_names())
    counts: dict[str, int] = {}
    skipped: dict[str, set] = {}  # table -> ids left behind, so their chats, quizzes... are too
    with source.connect() as src, target.begin() as dst:  # all or nothing
        for table in tables:
            rows = [dict(row._mapping) for row in src.execute(select(table))] if table.name in existing else []
            keep = []
            for row in rows:
                test_account = skip_test_accounts and table.name == "users" and row["email"].endswith(TEST_DOMAIN)
                orphan = any(row[fk.parent.name] in skipped.get(fk.column.table.name, ()) for fk in table.foreign_keys)
                if test_account or orphan:
                    skipped.setdefault(table.name, set()).add(row.get("id"))
                else:
                    keep.append(row)
            rows = keep
            if rows:
                dst.execute(table.insert(), rows)
            counts[table.name] = len(rows)
        if target.dialect.name == "postgresql":
            # The rows kept their ids, so move each id counter past them; otherwise the next
            # new account or chat would collide with a copied one.
            for table in tables:
                if "id" in table.c:
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    ))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy holox.db into the shared database in DATABASE_URL.")
    parser.add_argument("--source", default="holox.db", help="the SQLite file to copy (default: holox.db)")
    parser.add_argument("--keep-example-accounts", action="store_true", help="also copy @example.com test accounts")
    args = parser.parse_args()
    if settings.database_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL in backend/.env still points at a SQLite file. "
                         "Paste the shared database's connection string there first.")
    source = args.source if "://" in args.source else f"sqlite:///{args.source}"
    counts = copy_database(source, settings.database_url, skip_test_accounts=not args.keep_example_accounts)
    print("Copied into the shared database:")
    for name, count in counts.items():
        print(f"  {name:15s} {count}")


if __name__ == "__main__":
    main()
