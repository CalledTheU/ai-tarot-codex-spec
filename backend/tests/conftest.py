# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.database import create_db_engine, get_session
from app.main import app

BACKEND = Path(__file__).resolve().parents[1]


def migrate(engine, operation="upgrade", revision="head"):
    config = Config(str(BACKEND / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, operation)(config, revision)


@pytest.fixture
def db_engine(tmp_path):
    url = os.getenv("TEST_DATABASE_URL")
    admin = None
    if url:
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("TEST_DATABASE_URL must use postgresql+psycopg")
        schema = "test_tarot_" + uuid4().hex
        admin = create_db_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_db_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    try:
        migrate(engine)
        yield engine
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


@pytest.fixture
def database_app(db_engine):
    def session():
        with Session(db_engine) as db:
            yield db

    app.dependency_overrides[get_session] = session
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_session, None)
