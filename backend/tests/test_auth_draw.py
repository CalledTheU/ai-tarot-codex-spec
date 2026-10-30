# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import _attempts
from app.models import AuthSession, Reading, ReadingCard, Spread, TarotCard, User
from app.scripts.seed_cards import seed_catalog
from app.services.auth import digest, hasher

PASSWORD = "test passphrase 123!"
DRAW = {"question": " 如何理解当前的处境？ ", "category": "growth", "spread_id": "single-card"}


def account(client, email="owner@example.test"):
    data = {"email": email, "password": PASSWORD}
    assert client.post("/api/v1/auth/register", json=data).status_code == 201
    login = client.post("/api/v1/auth/login", json=data)
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}


@pytest.fixture
def client(database_app, db_engine):
    _attempts.clear()
    seed_catalog(db_engine)
    with TestClient(database_app) as client:
        yield client
    _attempts.clear()


def draw(client, headers, key="draw-1", **changes):
    return client.post(
        "/api/v1/readings", headers={**headers, "Idempotency-Key": key}, json={**DRAW, **changes}
    )


def test_auth_revocation_expiry_and_secrets(client, db_engine):
    headers = account(client, " Owner@Example.Test ")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.test"
    assert set(response.json()) == {"id", "email"}
    assert response.headers["Cache-Control"] == "no-store"
    with Session(db_engine) as session:
        user = session.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert hasher.verify(user.password_hash, PASSWORD)
        assert session.scalar(select(AuthSession)).token_hash == digest(
            headers["Authorization"][7:]
        )
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    data = {"email": "owner@example.test", "password": PASSWORD}
    token = client.post("/api/v1/auth/login", json=data).json()["access_token"]
    with Session(db_engine) as session, session.begin():
        auth = session.scalar(select(AuthSession))
        auth.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token}).status_code
        == 401
    )
    wrong = client.post("/api/v1/auth/login", json={**data, "password": "incorrect password"})
    missing = client.post("/api/v1/auth/login", json={**data, "email": "missing@example.test"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["error"]["message"] == missing.json()["error"]["message"]
    assert client.post("/api/v1/auth/register", json=data).status_code == 400


@pytest.mark.parametrize(
    "spread,count",
    [
        ("single-card", 1),
        ("three-card-past-present-future", 3),
        ("three-card-situation-challenge-advice", 3),
        ("five-card-reflection", 5),
    ],
)
def test_draw_and_idempotency(client, db_engine, spread, count):
    headers = account(client)
    response = draw(client, headers, spread_id=spread)
    assert response.status_code == 201, response.text
    reading = response.json()
    cards = reading["cards"]
    assert reading["question"] == DRAW["question"].strip()
    assert reading["status"] == "pending_interpretation"
    assert len(cards) == len({c["card_id"] for c in cards}) == count
    assert {c["position_index"] for c in cards} == set(range(count))
    assert all(c["orientation"] in {"upright", "reversed"} for c in cards)
    assert reading["draw_metadata"]["algorithm"] == "secrets-sample-v1"
    assert draw(client, headers, spread_id=spread).json() == reading
    assert draw(client, headers, question="另一个问题", spread_id=spread).status_code == 409
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(Reading)) == 1
        assert session.scalar(select(func.count()).select_from(ReadingCard)) == count


def test_snapshots_survive_catalog_edits_and_permissions(client, db_engine):
    owner, other = account(client), account(client, "other@example.test")
    reading = draw(client, owner).json()
    from uuid import UUID

    with Session(db_engine) as session, session.begin():
        card = session.get(TarotCard, UUID(reading["cards"][0]["card_id"]))
        card.upright_meaning = "Changed later"
        spread = session.get(Spread, UUID(reading["spread"]["id"]))
        spread.name = "Changed later"
        spread.is_active = False
    url = "/api/v1/readings/" + reading["id"]
    assert client.get(url, headers=owner).json() == reading
    assert draw(client, owner).json() == reading  # replay even after spread disabled
    assert client.get(url, headers=other).status_code == 404
    assert client.get(url).status_code == 401
    assert draw(client, {}).status_code == 401
    assert draw(client, other, key="other").status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"question": " "},
        {"question": "x" * 1001},
        {"background": "x" * 5001},
        {"category": "bad"},
        {"user_id": "other"},
        {"cards": []},
        {"orientation": "upright"},
    ],
)
def test_draw_input_rejects_overrides(client, changes):
    assert draw(client, account(client), **changes).status_code == 422


def test_auth_rate_limit_and_disabled_user(client, db_engine, monkeypatch):
    from app.config import settings

    headers = account(client)
    with Session(db_engine) as session, session.begin():
        session.scalar(select(User)).is_active = False
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    monkeypatch.setattr(
        type(settings), "auth_requests_per_minute", property(lambda _: 1), raising=False
    )
    _attempts.clear()
    data = {"email": "missing@example.test", "password": PASSWORD}
    assert client.post("/api/v1/auth/login", json=data).status_code == 401
    assert client.post("/api/v1/auth/login", json=data).status_code == 429


def test_concurrent_idempotency_postgresql(client, db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    headers = account(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: draw(client, headers), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()


def test_password_whitespace_and_input_policy(client):
    password = "  long passphrase 123  "
    credentials = {"email": "spaces@example.test", "password": password}
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
    assert (
        client.post(
            "/api/v1/auth/login", json={**credentials, "password": password.strip()}
        ).status_code
        == 401
    )
    for changes in (
        {"email": "invalid"},
        {"password": "short"},
        {"password": "x" * 129},
        {"extra": "bad"},
    ):
        assert (
            client.post("/api/v1/auth/register", json={**credentials, **changes}).status_code == 422
        )


def test_missing_idempotency_key_and_draw_rate_limit(client, monkeypatch):
    from dataclasses import replace

    from app.services import readings as service

    headers = account(client)
    assert client.post("/api/v1/readings", headers=headers, json=DRAW).status_code == 422
    monkeypatch.setattr(service, "settings", replace(service.settings, readings_per_minute=1))
    first = draw(client, headers)
    assert first.status_code == 201
    assert draw(client, headers, key="another").status_code == 429
    assert draw(client, headers).json() == first.json()
