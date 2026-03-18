from sqlmodel import SQLModel, create_engine, Session
import os
from typing import Generator
from sqlalchemy.pool import StaticPool


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./citypulse.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

if DATABASE_URL.startswith("sqlite"):
    # For sqlite, use StaticPool and do not pass pool_size/max_overflow:
    # StaticPool manages pooling internally and rejects those arguments.
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args=connect_args,
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args=connect_args,
        pool_size=1,
        max_overflow=0,
    )


def init_db() -> None:
    """Create all database tables."""
    # Import models so that SQLModel is aware of them before creating tables.
    import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)


def get_session_dep() -> Generator[Session, None, None]:
    """FastAPI dependency that guarantees the DB session is closed."""
    with Session(engine) as session:
        yield session


