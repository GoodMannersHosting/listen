from __future__ import annotations

import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    # sqlite:///./data/listen.db -> ./data/listen.db
    path = url.split("sqlite:///")[-1]
    if path.startswith("./"):
        path = path[2:]
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, _connection_record):
    # SQLite pragmas for better concurrency and FK integrity
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema() -> None:
    """
    Lightweight schema migration helper for SQLite.

    We avoid a full migration framework for this MVP, but we still need to keep
    existing DBs compatible when we add new columns.
    """
    from app.models import Base

    # Create missing tables.
    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(uploads)")).fetchall()]
        if "tags" not in cols:
            conn.execute(text("ALTER TABLE uploads ADD COLUMN tags TEXT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_healthcheck() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

