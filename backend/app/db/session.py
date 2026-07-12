"""
Database engine & session factory.

Uses a synchronous SQLAlchemy engine with connection pooling tuned for
enterprise workloads. Switch to `create_async_engine` + asyncpg if the
team later moves to fully async repositories - schema/models are
compatible with both.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    str(settings.DATABASE_URI),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # avoids "server closed the connection unexpectedly" after idle
    echo=settings.DB_ECHO,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency - yields a request-scoped DB session and
    guarantees it is closed even if the endpoint raises."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
