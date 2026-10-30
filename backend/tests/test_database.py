# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import importlib.util
import json
from io import StringIO
from uuid import uuid4

import pytest
from conftest import BACKEND, migrate
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.catalog_data import CardData, SpreadData, load_seed_data
from app.database import get_session
from app.models import AgentRun, Base, ChatMessage, Reading, ReadingCard, Spread, TarotCard, User
from app.scripts.seed_cards import seed_catalog


def test_catalog_matches_source_snapshot():
    root = BACKEND.parent
    spec = importlib.util.spec_from_file_location(
        "build_catalog", root / "scripts/build_catalog.py"
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    cards, spreads = load_seed_data()
    assert len(cards) == 78
    rebuilt = [
        CardData.model_validate(c)
        for c in builder.build_cards(builder.SOURCE.read_text(encoding="utf-8"))
    ]
    assert cards == rebuilt
    assert spreads == [SpreadData.model_validate(s) for s in builder.build_spreads()]
    assert next(c for c in cards if c.slug == "two-of-cups").reversed_meaning == "Passion."


def test_migration_roundtrip_and_model_agreement(db_engine):
    expected = set(Base.metadata.tables)
    assert set(inspect(db_engine).get_table_names()) == expected | {"alembic_version"}
    migrate(db_engine)
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []
    migrate(db_engine, "downgrade", "base")
    assert set(inspect(db_engine).get_table_names()) == {"alembic_version"}
    migrate(db_engine)
    assert set(inspect(db_engine).get_table_names()) == expected | {"alembic_version"}


def test_postgresql_migration_sql():
    output = StringIO()
    config = Config(str(BACKEND / "alembic.ini"), output_buffer=output)
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://unused/unused")
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "JSONB" in sql and "UUID" in sql and "TIMESTAMP WITH TIME ZONE" in sql
    assert "ON DELETE CASCADE" in sql


def test_phase34_migration_preserves_existing_records(db_engine):
    from sqlalchemy import MetaData, Table, text

    migrate(db_engine, "downgrade", "0001")
    uid = uuid4()
    with db_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, :hash)"),
            {
                "id": uid.hex if db_engine.dialect.name == "sqlite" else uid,
                "email": "existing@example.test",
                "hash": "existing-hash",
            },
        )
    seed_catalog(db_engine)
    rid = uuid4()
    table = Table("readings", MetaData(), autoload_with=db_engine)
    with db_engine.begin() as connection:
        spread_id = connection.scalar(select(Spread.id))
        connection.execute(
            table.insert().values(
                id=rid.hex if db_engine.dialect.name == "sqlite" else rid,
                user_id=uid.hex if db_engine.dialect.name == "sqlite" else uid,
                spread_id=spread_id.hex if db_engine.dialect.name == "sqlite" else spread_id,
                question="Existing private question",
                category="growth",
                status="pending_interpretation",
                spread_snapshot={"name": "Original spread"},
                cards_snapshot=[{"original": "snapshot"}],
            )
        )
    migrate(db_engine)
    with Session(db_engine) as session:
        user = session.get(User, uid)
        assert user.email == "existing@example.test" and user.password_hash == "existing-hash"
        reading = session.get(Reading, rid)
        assert reading.question == "Existing private question"
        assert reading.cards_snapshot == [{"original": "snapshot"}]
        assert reading.spread_snapshot == {"name": "Original spread"}
        assert reading.idempotency_key is None and reading.active_run_id is None
    seed_catalog(db_engine)


def test_seed_is_idempotent_and_preserves_existing_data(db_engine):
    assert seed_catalog(db_engine) == {"cards": 78, "spreads": 4}
    with Session(db_engine) as session, session.begin():
        card = session.scalar(select(TarotCard).where(TarotCard.slug == "the-fool"))
        card.name_zh = "用户维护的名称"
        session.add(User(email="owner@example.test", password_hash="test-only-hash"))
        spread = session.scalar(select(Spread).where(Spread.slug == "single-card"))
        spread.is_active = False
    assert seed_catalog(db_engine) == {"cards": 0, "spreads": 0}
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(TarotCard)) == 78
        assert session.scalar(select(func.count()).select_from(Spread)) == 4
        assert session.scalar(select(User)).email == "owner@example.test"
        assert session.scalar(select(TarotCard).where(TarotCard.slug == "the-fool")).name_zh == (
            "用户维护的名称"
        )
        assert not session.scalar(select(Spread).where(Spread.slug == "single-card")).is_active


def test_foreign_keys_uniqueness_checks_and_cascade(db_engine):
    seed_catalog(db_engine)
    with Session(db_engine) as session, session.begin():
        user = User(email="owner@example.test", password_hash="test-only-hash")
        session.add(user)
        session.flush()
        card = session.scalar(select(TarotCard))
        spread = session.scalar(select(Spread))
        reading = Reading(
            user_id=user.id,
            spread_id=spread.id,
            spread_snapshot={},
            question="测试",
            category="growth",
            status="pending_interpretation",
            cards_snapshot=[],
        )
        session.add(reading)
        session.flush()
        rid, cid = reading.id, card.id
        other_cid = session.scalar(select(TarotCard.id).where(TarotCard.id != cid))
        session.add(
            ReadingCard(
                reading_id=rid,
                card_id=cid,
                position_index=0,
                position_name="主题",
                orientation="upright",
                card_snapshot={},
            )
        )
        session.add(ChatMessage(reading_id=rid, role="user", content="测试"))
        session.add(AgentRun(reading_id=rid, status="running"))
    for values in (
        {"card_id": cid, "position_index": 1, "orientation": "upright"},
        {"card_id": other_cid, "position_index": 0, "orientation": "reversed"},
        {"card_id": other_cid, "position_index": 2, "orientation": "invalid"},
        {"card_id": uuid4(), "position_index": 2, "orientation": "upright"},
    ):
        with pytest.raises(IntegrityError), Session(db_engine) as session, session.begin():
            session.add(
                ReadingCard(reading_id=rid, position_name="测试", card_snapshot={}, **values)
            )
    with pytest.raises(IntegrityError), Session(db_engine) as session, session.begin():
        session.add(User(email=" OWNER@EXAMPLE.TEST ", password_hash="test-only-hash"))
    with Session(db_engine) as session, session.begin():
        session.execute(delete(Reading).where(Reading.id == rid))
    with Session(db_engine) as session:
        for model in (ReadingCard, ChatMessage, AgentRun):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("corruption", ["missing_card", "meaning", "positions"])
def test_invalid_seed_is_rejected_before_writes(db_engine, tmp_path, corruption):
    directory = tmp_path / "invalid_seed"
    directory.mkdir()
    data = BACKEND / "app/data"
    cards = json.loads((data / "cards.json").read_text(encoding="utf-8"))
    spreads = json.loads((data / "spreads.json").read_text(encoding="utf-8"))
    if corruption == "missing_card":
        cards.pop()
    elif corruption == "meaning":
        cards[0]["upright_meaning"] = "Untraceable replacement"
    else:
        spreads[1]["positions"][1]["index"] = 0
    (directory / "cards.json").write_text(json.dumps(cards), encoding="utf-8")
    (directory / "spreads.json").write_text(json.dumps(spreads), encoding="utf-8")
    with pytest.raises(ValueError):
        seed_catalog(db_engine, directory)
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(TarotCard)) == 0
        assert session.scalar(select(func.count()).select_from(Spread)) == 0


def test_ready_fails_without_database_but_live_survives(database_app):
    def broken_session():
        raise OperationalError("private SQL", {}, Exception("private connection"))
        yield

    database_app.dependency_overrides[get_session] = broken_session
    with TestClient(database_app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert "private" not in response.text
        assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
        assert client.get("/health/live").status_code == 200
