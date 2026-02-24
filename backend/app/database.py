import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

LOCAL_DEFAULT_DATABASE_URL = "postgresql+psycopg:///badminton_b7g"


def normalize_database_url(raw_url: str | None) -> str:
    value = (raw_url or "").strip()
    if not value:
        value = os.getenv("LOCAL_DATABASE_URL", LOCAL_DEFAULT_DATABASE_URL).strip()

    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)

    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)

    return value


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

engine_kwargs: dict[str, object] = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
