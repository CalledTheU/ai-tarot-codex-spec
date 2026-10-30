# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import asyncio
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_auth_draw import account, draw

from app.api.auth import _attempts
from app.config import Settings
from app.database import get_session
from app.llm import ModelResult, ModelUnavailable, OpenAICompatibleAdapter, get_model
from app.models import AgentRun, Reading, ReadingCard
from app.scripts.seed_cards import seed_catalog


def valid_output(prompt):
    cards = json.loads(prompt)["untrusted_context"]["cards"]
    return {
        "summary": "示例反思",
        "scope_note": "不具有预测效力，仅为反思",
        "card_interpretations": [
            {
                k: c[k]
                for k in (
                    "card_id",
                    "position_index",
                    "position_name",
                    "orientation",
                    "traditional_meaning",
                )
            }
            | {"contextual_interpretation": "一种可能的观察角度", "source_ids": [c["source_id"]]}
            for c in cards
        ],
        "synthesis": "综合反思",
        "possible_scenarios": [{"description": "可能的方向", "basis": "象征"}],
        "action_suggestions": ["先记录自己的需要"],
        "reflection_questions": ["你关心什么？"],
        "uncertainties": ["无法知道他人想法"],
    }


class FakeModel:
    provider = "test-only"
    model_name = "mock-structured"

    def __init__(self):
        self.prompts = []
        self.behavior = None
        self.sessions = []

    async def generate(self, prompt):
        assert not any(session.in_transaction() for session in self.sessions)
        self.prompts.append(prompt)
        if self.behavior:
            return await self.behavior(prompt)
        return ModelResult(json.dumps(valid_output(prompt)), {"total_tokens": 123})


@pytest.fixture
def setup(database_app, db_engine):
    _attempts.clear()
    seed_catalog(db_engine)
    model = FakeModel()

    def sessions():
        with Session(db_engine) as session:
            model.sessions.append(session)
            yield session
            model.sessions.remove(session)

    database_app.dependency_overrides[get_session] = sessions
    database_app.dependency_overrides[get_model] = lambda: model
    with TestClient(database_app) as client:
        headers = account(client)
        reading = draw(client, headers, spread_id="three-card-past-present-future").json()
        yield client, headers, reading, model
    database_app.dependency_overrides.pop(get_model, None)
    _attempts.clear()


def interpret(client, headers, reading, **options):
    return client.post(f"/api/v1/readings/{reading['id']}/interpret", headers=headers, json=options)


def test_success_cached_and_snapshot_only(setup, db_engine):
    client, headers, reading, model = setup
    response = interpret(client, headers, reading)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed" and len(body["sources"]) == 3
    assert {s["source_id"] for s in body["sources"]} == {
        c["source_ids"][0] for c in body["interpretation"]["card_interpretations"]
    }
    assert interpret(client, headers, reading).json() == body
    assert interpret(client, headers, reading, include_sources=False).json()["sources"] == []
    assert len(model.prompts) == 1
    detail = client.get("/api/v1/readings/" + reading["id"], headers=headers).json()
    assert detail["cards"] == reading["cards"] and detail["spread"] == reading["spread"]
    assert detail["interpretation"] == body["interpretation"]
    with Session(db_engine) as session:
        run = session.scalar(select(AgentRun))
        assert run.status == "completed" and run.prompt_version == "basic-interpretation-v1"
        assert run.diagnostics["usage"] == {"total_tokens": 123}
        assert "background" not in run.diagnostics


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "json",
        "provider",
        "unexpected",
        "missing",
        "extra",
        "card_id",
        "position",
        "position_name",
        "orientation",
        "source",
        "meaning",
        "duplicate",
        "omitted",
        "large",
    ],
)
def test_failure_retry_never_redraws(setup, db_engine, failure):
    client, headers, reading, model = setup

    async def fail(prompt):
        if failure == "timeout":
            raise TimeoutError("secret timeout detail")
        if failure == "provider":
            raise ModelUnavailable("secret API key")
        if failure == "unexpected":
            raise RuntimeError("secret provider detail")
        if failure == "json":
            return ModelResult("not-json secret")
        if failure == "large":
            return ModelResult("x" * 64001)
        output = valid_output(prompt)
        item = output["card_interpretations"][0]
        if failure == "missing":
            output.pop("summary")
        if failure == "extra":
            output["untrusted_extra"] = "override"
        if failure == "card_id":
            item["card_id"] = str(uuid4())
        if failure == "position":
            item["position_index"] = 999
        if failure == "position_name":
            item["position_name"] = "伪造牌位"
        if failure == "orientation":
            item["orientation"] = "reversed" if item["orientation"] == "upright" else "upright"
        if failure == "source":
            item["source_ids"] = ["invented-source"]
        if failure == "meaning":
            item["traditional_meaning"] = "invented traditional meaning"
        if failure == "duplicate":
            output["card_interpretations"][1] = copy.deepcopy(item)
        if failure == "omitted":
            output["card_interpretations"].pop()
        return ModelResult(json.dumps(output))

    model.behavior = fail
    response = interpret(client, headers, reading)
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert "secret" not in response.text
    failed = client.get("/api/v1/readings/" + reading["id"], headers=headers).json()
    assert failed["status"] == "failed" and failed["interpretation"] is None
    for key in ("cards", "spread", "draw_metadata"):
        assert failed[key] == reading[key]
    with Session(db_engine) as session:
        rows = list(
            session.scalars(
                select(ReadingCard)
                .where(ReadingCard.reading_id == UUID(reading["id"]))
                .order_by(ReadingCard.position_index)
            )
        )
        before = [(r.card_id, r.orientation, r.position_index, r.card_snapshot) for r in rows]
        run = session.scalar(select(AgentRun))
        assert run.status == "failed" and "secret" not in json.dumps(run.diagnostics)
    model.behavior = None
    success = interpret(client, headers, reading)
    assert success.status_code == 200, success.text
    assert (
        json.loads(model.prompts[0])["untrusted_context"]
        == json.loads(model.prompts[1])["untrusted_context"]
    )
    with Session(db_engine) as session:
        after = list(
            session.scalars(
                select(ReadingCard)
                .where(ReadingCard.reading_id == UUID(reading["id"]))
                .order_by(ReadingCard.position_index)
            )
        )
        assert before == [
            (r.card_id, r.orientation, r.position_index, r.card_snapshot) for r in after
        ]
        assert len(list(session.scalars(select(AgentRun)))) == 2
        assert len(list(session.scalars(select(Reading)))) == 1


def test_interpret_authorization_and_overrides(setup):
    client, headers, reading, model = setup
    other = account(client, "other@example.test")
    assert interpret(client, {}, reading).status_code == 401
    assert interpret(client, other, reading).status_code == 404
    for override in ({"cards": []}, {"user_id": str(uuid4())}, {"style": "invalid"}):
        assert interpret(client, headers, reading, **override).status_code == 422
    assert not model.prompts


def test_unconfigured_model_does_not_break_draw(setup):
    client, headers, reading, model = setup
    model.behavior = OpenAICompatibleAdapter(Settings(llm_model="", llm_base_url="")).generate
    assert interpret(client, headers, reading).status_code == 503
    assert draw(client, headers, key="still-can-draw").status_code == 201


def test_stale_processing_recovers_and_fences_late_completion(setup, db_engine):
    from fastapi import HTTPException

    from app.services.interpretation import finish

    client, headers, reading, model = setup
    old_id = uuid4()
    with Session(db_engine) as session, session.begin():
        row = session.get(Reading, UUID(reading["id"]))
        user_id = row.user_id
        row.status, row.active_run_id = "processing", old_id
        session.add(
            AgentRun(
                id=old_id,
                reading_id=row.id,
                status="running",
                started_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
    assert interpret(client, headers, reading).status_code == 200
    with Session(db_engine) as session:
        assert session.get(AgentRun, old_id).error_code == "RUN_EXPIRED"
        with pytest.raises(HTTPException) as exc:
            finish(session, user_id, UUID(reading["id"]), old_id, {"bad": "late result"}, None, {})
        assert exc.value.status_code == 409


def test_concurrent_interpretation_postgresql(setup, db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    client, headers, reading, model = setup
    entered, release = Event(), Event()

    async def wait(prompt):
        entered.set()
        assert await asyncio.to_thread(release.wait, 10)
        return ModelResult(json.dumps(valid_output(prompt)))

    model.behavior = wait
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(interpret, client, headers, reading)
        try:
            assert entered.wait(10)
            assert interpret(client, headers, reading).status_code == 409
            second_reading = draw(client, headers, key="second-reading").json()
            assert interpret(client, headers, second_reading).status_code == 429
        finally:
            release.set()
        assert first.result(timeout=10).status_code == 200
    assert len(model.prompts) == 1


def test_http_adapter_contract_and_usage():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                "usage": {"total_tokens": 10, "private": "never-store"},
            },
        )

    config = replace(
        Settings(), llm_base_url="http://local-model.test/v1", llm_model="configured-model"
    )
    result = asyncio.run(
        OpenAICompatibleAdapter(config, httpx.MockTransport(respond)).generate("context")
    )
    assert result == ModelResult("{}", {"total_tokens": 10})
    assert str(seen[0].url) == "http://local-model.test/v1/chat/completions"
    payload = json.loads(seen[0].content)
    assert (
        payload["messages"][0]["role"] == "system"
        and payload["messages"][1]["content"] == "context"
    )
    assert payload["model"] == "configured-model" and payload["response_format"] == {
        "type": "json_object"
    }


@pytest.mark.parametrize("kind", ["timeout", "429", "500", "invalid", "truncated", "large"])
def test_http_adapter_failure(kind):
    def respond(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("private", request=request)
        if kind in {"429", "500"}:
            return httpx.Response(int(kind), text="secret")
        if kind == "invalid":
            return httpx.Response(200, text="not-json")
        if kind == "large":
            return httpx.Response(200, content=b"x" * 262145)
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}
        )

    config = Settings(llm_base_url="http://local-model.test/v1", llm_model="test")
    with pytest.raises(ModelUnavailable):
        asyncio.run(
            OpenAICompatibleAdapter(config, httpx.MockTransport(respond)).generate("context")
        )


def test_real_timeout_boundary_and_retry(setup, monkeypatch):
    from app.services import interpretation as service

    client, headers, reading, model = setup
    monkeypatch.setattr(service, "settings", replace(service.settings, llm_timeout_seconds=1))

    async def too_slow(prompt):
        await asyncio.sleep(10)
        return ModelResult(json.dumps(valid_output(prompt)))

    model.behavior = too_slow
    assert interpret(client, headers, reading).status_code == 503
    model.behavior = None
    assert interpret(client, headers, reading).status_code == 200
    assert (
        json.loads(model.prompts[0])["untrusted_context"]
        == json.loads(model.prompts[1])["untrusted_context"]
    )


def test_rate_and_global_concurrency_limits(setup, monkeypatch):
    from threading import BoundedSemaphore

    from app.services import interpretation as service

    client, headers, reading, model = setup
    slots = BoundedSemaphore(1)
    monkeypatch.setattr(service, "model_slots", slots)
    slots.acquire()
    try:
        assert interpret(client, headers, reading).status_code == 429
        assert not model.prompts
    finally:
        slots.release()
    monkeypatch.setattr(service, "settings", replace(service.settings, model_requests_per_minute=1))

    async def fail(prompt):
        raise TimeoutError()

    model.behavior = fail
    assert interpret(client, headers, reading).status_code == 503
    assert interpret(client, headers, reading).status_code == 429


@pytest.mark.parametrize(
    "changes",
    [
        {"llm_base_url": "", "llm_model": "missing-endpoint"},
        {"llm_base_url": "http://localhost/v1", "llm_model": ""},
        {"llm_base_url": "file:///tmp/model", "llm_model": "test"},
        {"llm_base_url": "https://user:password@example.test/v1", "llm_model": "test"},
        {"llm_base_url": "http://localhost/v1", "llm_model": "test", "llm_provider": "unknown"},
    ],
)
def test_invalid_model_configuration_never_sends_request(changes):
    def no_request(request):
        pytest.fail("Invalid configuration must not call a model")

    with pytest.raises(ModelUnavailable):
        asyncio.run(
            OpenAICompatibleAdapter(Settings(**changes), httpx.MockTransport(no_request)).generate(
                "context"
            )
        )
