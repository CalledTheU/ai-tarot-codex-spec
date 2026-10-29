# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Spread
from app.scripts.seed_cards import seed_catalog


@pytest.fixture
def client(database_app, db_engine):
    seed_catalog(db_engine)
    with TestClient(database_app) as client:
        yield client


def test_cards_pagination_and_detail(client):
    first = client.get("/api/v1/cards").json()
    assert (first["total"], first["page"], first["page_size"]) == (78, 1, 20)
    assert len(first["items"]) == 20
    assert first["items"][0]["slug"] == "the-fool"
    second = client.get("/api/v1/cards?page=2").json()
    assert not {c["id"] for c in first["items"]} & {c["id"] for c in second["items"]}
    assert client.get("/api/v1/cards?page=100").json()["items"] == []
    detail = client.get("/api/v1/cards/the-fool")
    assert detail.status_code == 200
    card = detail.json()
    assert client.get(f"/api/v1/cards/{card['id']}").json() == card
    assert card["source_reference"]["source_id"] == "pg-43548"
    assert card["upright_meaning"] and card["reversed_meaning"]
    assert "created_at" not in card and "updated_at" not in card
    assert "upright_meaning" not in first["items"][0]


@pytest.mark.parametrize(
    ("params", "total"),
    [
        ({"arcana_type": "major"}, 22),
        ({"arcana_type": "minor"}, 56),
        ({"suit": "cups"}, 14),
        ({"q": " 愚者 "}, 1),
        ({"q": "mAgIcIaN"}, 1),
        ({"q": "%"}, 0),
        ({"q": "_"}, 0),
        ({"q": "' OR 1=1 --"}, 0),
        ({"q": "不存在"}, 0),
        ({"arcana_type": "major", "suit": "cups"}, 0),
    ],
)
def test_filters_and_literal_search(client, params, total):
    response = client.get("/api/v1/cards", params=params)
    assert response.status_code == 200
    assert response.json()["total"] == total


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=999999999999999999999999999999999999999",
        "page=-1",
        "page_size=0",
        "page_size=101",
        "page=invalid",
        "arcana_type=invalid",
        "suit=invalid",
        "q=" + "a" * 101,
    ],
)
def test_invalid_filters(client, query):
    response = client.get("/api/v1/cards?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "path",
    [
        "/cards/missing",
        "/cards/not-a-uuid",
        "/spreads/missing",
        "/cards/00000000-0000-0000-0000-000000000000",
    ],
)
def test_not_found(client, path):
    response = client.get("/api/v1" + path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_spreads_and_inactive_visibility(client, db_engine):
    response = client.get("/api/v1/spreads")
    assert response.status_code == 200
    spreads = response.json()
    assert sorted(len(s["positions"]) for s in spreads) == [1, 3, 3, 5]
    for spread in spreads:
        assert client.get(f"/api/v1/spreads/{spread['slug']}").json() == spread
        assert client.get(f"/api/v1/spreads/{spread['id']}").json() == spread
        assert "is_active" not in spread
    with Session(db_engine) as session, session.begin():
        item = session.scalar(select(Spread).where(Spread.slug == "single-card"))
        inactive_id = item.id
        item.is_active = False
    assert len(client.get("/api/v1/spreads").json()) == 3
    assert client.get("/api/v1/spreads/single-card").status_code == 404
    assert client.get(f"/api/v1/spreads/{inactive_id}").status_code == 404


def test_catalog_works_without_model_configuration(client, monkeypatch):
    for name in ("LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert client.get("/api/v1/cards?page_size=100").json()["total"] == 78
    assert len(client.get("/api/v1/spreads").json()) == 4
