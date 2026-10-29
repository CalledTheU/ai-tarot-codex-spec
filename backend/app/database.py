# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.config import settings


def create_db_engine(url: str):
    sqlite = url.startswith("sqlite:")
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if sqlite else {"connect_timeout": 3},
    )
    if sqlite:

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


@lru_cache
def get_engine():
    return create_db_engine(settings.database_url)


def get_session():
    with Session(get_engine()) as session:
        yield session
