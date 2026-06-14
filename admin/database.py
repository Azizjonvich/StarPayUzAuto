"""SQLAlchemy database setup — sync mode for Windows without greenlet"""
import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from admin.config import DATABASE_URL

logger = logging.getLogger(__name__)

# SQLite requires check_same_thread=False for FastAPI
_engine_url = DATABASE_URL
connect_args = {}
if _engine_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(_engine_url, connect_args=connect_args, echo=False)
SessionFactory = sessionmaker(engine, class_=Session, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a sync SQLAlchemy session."""
    with SessionFactory() as session:
        try:
            yield session
        finally:
            session.close()


def init_models():
    """Create all tables defined in models."""
    from admin.models import admin_user, log, setting, broadcast, transaction
    Base.metadata.create_all(engine)
    logger.info("Admin panel database tables created/verified")


def dispose_engine():
    engine.dispose()
