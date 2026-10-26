from app.database import engine_options, engine_url


def test_cloud_connection_strings_work_as_pasted():
    neon = "postgresql://user:secret@ep-cool-name.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert engine_url(neon) == "postgresql+psycopg://user:secret@ep-cool-name.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert engine_url("postgres://u:p@db.example.supabase.co:5432/postgres").startswith("postgresql+psycopg://u:p@")


def test_other_urls_are_left_alone():
    for url in ("sqlite:///./holox.db", "sqlite://", "postgresql+psycopg://u:p@host/db"):
        assert engine_url(url) == url


def test_cloud_connections_are_checked_before_use():
    assert engine_options("postgresql://u:p@host/db") == {"pool_pre_ping": True, "pool_recycle": 300}
    assert engine_options("sqlite:///./holox.db") == {"connect_args": {"check_same_thread": False}}
