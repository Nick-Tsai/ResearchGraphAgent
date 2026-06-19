"""Database engine and session management."""

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event
from app.config import DATABASE_URL

if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL, echo=False)


def _ensure_sqlite_compat_columns() -> None:
    if "sqlite" not in DATABASE_URL:
        return
    with engine.begin() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(projects)").fetchall()}
        if "current_node" not in columns:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN current_node TEXT DEFAULT 'draft'")
        if "progress_state" not in columns:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN progress_state TEXT DEFAULT 'complete'")


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_compat_columns()


def get_session() -> Session:
    with Session(engine) as session:
        yield session
