"""Database engine, session factory and the declarative Base class.

This is the lowest layer of the app (the "Data Layer" plumbing). Everything
that talks to the database goes through the SessionLocal factory defined here.
Business logic never creates its own connection; it always receives a Session.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs a special flag because, by default, a connection may only be used
# by the thread that created it. FastAPI serves requests from a thread pool, so
# we relax that rule. The flag is ignored for PostgreSQL.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

# The engine is the actual pool of database connections. Created once, reused.
engine = create_engine(settings.database_url, connect_args=connect_args)

# A factory that hands out new Session objects. A Session is one "unit of work":
# you open it, run queries/inserts inside it, then commit or roll back.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Parent class for every ORM model.

    SQLAlchemy collects table definitions from all classes that inherit from
    this Base, which is how Alembic and create_all() know what tables to build.
    """


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    The try/finally guarantees the session is always closed, even if the
    request handler raises an error, so we never leak connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
