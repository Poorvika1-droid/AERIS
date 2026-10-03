from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

if settings.database_url.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,  # wait up to 30 s before raising "database is locked"
    }
    engine_options = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
        # Single writer at a time is safest for SQLite; no pool needed
        "pool_size": 1,
        "max_overflow": 0,
    }
else:
    connect_args = {}
    engine_options = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
        "pool_recycle": 1800,  # recycle before MySQL closes idle connections
    }

engine = create_engine(settings.database_url, **engine_options)

# Enable WAL mode for SQLite — allows readers and one writer to coexist
if settings.database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
