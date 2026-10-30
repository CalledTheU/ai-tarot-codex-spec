# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import settings
from app.llm import ModelUnavailable
from app.models import AgentRun, Reading
from app.repositories.readings import lock_user
from app.schemas import Interpretation
from app.services.readings import require_owned

PROMPT_VERSION = "basic-interpretation-v1"
# shortcut: global model concurrency is per worker; run one worker until proxy-wide limits exist.
model_slots = BoundedSemaphore(settings.model_max_concurrency)


def source_context(reading):
    cards, sources = [], []
    for card in reading.cards_snapshot:
        snapshot = card["card_snapshot"]
        reference = snapshot["source_reference"]
        source_id = ":".join(
            (
                reference["source_id"],
                card["card_id"],
                card["orientation"],
                snapshot["content_version"],
            )
        )
        excerpt = snapshot[card["orientation"] + "_meaning"]
        cards.append(
            {
                k: card[k]
                for k in ("card_id", "name", "position_index", "position_name", "orientation")
            }
            | {"traditional_meaning": excerpt, "source_id": source_id}
        )
        url = reference.get("reversed_url") if card["orientation"] == "reversed" else None
        sources.append(
            {
                "source_id": source_id,
                "card_id": card["card_id"],
                "orientation": card["orientation"],
                "excerpt": excerpt,
                "reference": {**reference, "url": url or reference["url"]},
                "content_version": snapshot["content_version"],
            }
        )
    return cards, sources


def validate(text, cards):
    if len(text) > 64000:
        raise ValueError("MODEL_RESPONSE_TOO_LARGE")
    output = Interpretation.model_validate_json(text)
    expected = {c["position_index"]: c for c in cards}
    seen = set()
    for item in output.card_interpretations:
        original = expected.get(item.position_index)
        if original is None or item.position_index in seen:
            raise ValueError("CARD_MISMATCH")
        seen.add(item.position_index)
        for key in ("card_id", "position_name", "orientation"):
            if str(getattr(item, key)) != original[key]:
                raise ValueError("CARD_MISMATCH")
        if item.source_ids != [original["source_id"]]:
            raise ValueError("SOURCE_MISMATCH")
        if item.traditional_meaning != original["traditional_meaning"].strip():
            raise ValueError("MEANING_MISMATCH")
    if seen != set(expected):
        raise ValueError("CARD_MISMATCH")
    return output.model_dump(mode="json")


def result(reading, sources, include_sources):
    return {
        "reading_id": reading.id,
        "status": "completed",
        "interpretation": reading.interpretation,
        "sources": sources if include_sources else [],
        "run_id": reading.active_run_id,
    }


def claim(session, user_id, reading_id, adapter):
    lock_user(session, user_id)
    reading = require_owned(session, reading_id, user_id, lock=True)
    cards, sources = source_context(reading)
    if reading.status == "completed":
        session.commit()
        return reading, cards, sources, None
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.llm_timeout_seconds + 30)
    if reading.status == "processing":
        previous = session.get(AgentRun, reading.active_run_id) if reading.active_run_id else None
        started = previous.started_at if previous else reading.updated_at
        started = started.replace(tzinfo=UTC) if started.tzinfo is None else started.astimezone(UTC)
        if started > cutoff:
            raise HTTPException(409, "解读正在生成，请稍后刷新")
        if previous:
            previous.status, previous.error_code, previous.finished_at = (
                "failed",
                "RUN_EXPIRED",
                now,
            )
    runs = (
        select(AgentRun)
        .join(Reading, AgentRun.reading_id == Reading.id)
        .where(Reading.user_id == user_id)
    )
    active = session.scalar(
        select(func.count()).select_from(
            runs.where(AgentRun.status == "running", AgentRun.started_at > cutoff).subquery()
        )
    )
    if active:
        raise HTTPException(429, "你已有解读正在生成，请稍后重试")
    recent = session.scalar(
        select(func.count()).select_from(
            runs.where(AgentRun.started_at > now - timedelta(minutes=1)).subquery()
        )
    )
    if recent >= settings.model_requests_per_minute:
        raise HTTPException(429, "解读请求过于频繁", headers={"Retry-After": "60"})
    run = AgentRun(
        id=uuid4(),
        reading_id=reading.id,
        status="running",
        provider=adapter.provider,
        model_name=adapter.model_name,
        prompt_version=PROMPT_VERSION,
        started_at=now,
        diagnostics={"retry_count": 0},
    )
    reading.status, reading.active_run_id = "processing", run.id
    session.add(run)
    # Commit the claim and immutable context before any external work.
    session.commit()
    return reading, cards, sources, run.id


def finish(session, user_id, reading_id, run_id, output, error, diagnostics):
    # The run ID fences late responses from an expired/crashed attempt.
    reading = require_owned(session, reading_id, user_id, lock=True)
    if reading.active_run_id != run_id or reading.status != "processing":
        raise HTTPException(409, "本次解读已过期，请刷新查看最新状态")
    run = session.get(AgentRun, run_id)
    run.status = "failed" if error else "completed"
    run.error_code = error
    run.finished_at = datetime.now(UTC)
    run.diagnostics = diagnostics
    reading.status = "failed" if error else "completed"
    if output is not None and error is None:
        reading.interpretation = output
        reading.interpretation_version = PROMPT_VERSION
    session.commit()
    return reading


async def interpret(session, user, reading_id, options, adapter):
    # Ownership is checked before acquiring a slot or considering model configuration.
    reading = require_owned(session, reading_id, user.id)
    if reading.status == "completed":
        return result(reading, source_context(reading)[1], options.include_sources)
    if not model_slots.acquire(blocking=False):
        raise HTTPException(429, "模型繁忙，请稍后重试")
    try:
        reading, cards, sources, run_id = claim(session, user.id, reading_id, adapter)
        if run_id is None:
            return result(reading, sources, options.include_sources)
        prompt = json.dumps(
            {
                "prompt_version": PROMPT_VERSION,
                "style": options.style,
                "output_schema": Interpretation.model_json_schema(),
                "untrusted_context": {
                    "question": reading.question,
                    "category": reading.category,
                    "background": reading.background,
                    "spread": reading.spread_snapshot,
                    "cards": cards,
                },
            },
            ensure_ascii=False,
        )
        # Access after commit may reopen an ORM transaction; explicitly close before HTTP.
        session.commit()
        started = time.monotonic()
        output, error, usage = None, None, {}
        try:
            response = await asyncio.wait_for(
                adapter.generate(prompt), timeout=settings.llm_timeout_seconds
            )
            output = validate(response.text, cards)
            usage = {
                k: v
                for k, v in response.usage.items()
                if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and type(v) is int
                and v >= 0
            }
        except (TimeoutError, asyncio.CancelledError) as exc:
            error = (
                "MODEL_CANCELLED" if isinstance(exc, asyncio.CancelledError) else "MODEL_TIMEOUT"
            )
            finish(
                session,
                user.id,
                reading_id,
                run_id,
                None,
                error,
                {"elapsed_ms": int((time.monotonic() - started) * 1000), "retry_count": 0},
            )
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise HTTPException(503, "模型暂时不可用，请保留原牌重试") from None
        except ModelUnavailable:
            error = "MODEL_UNAVAILABLE"
        except (ValidationError, ValueError, TypeError, AttributeError):
            error = "INVALID_MODEL_OUTPUT"
        except Exception:
            # Adapter implementations must not leak vendor exceptions or leave a running claim.
            error = "MODEL_UNAVAILABLE"
        reading = finish(
            session,
            user.id,
            reading_id,
            run_id,
            output,
            error,
            {
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "retry_count": 0,
                "usage": usage,
            },
        )
        if error:
            raise HTTPException(503, "模型暂时不可用，请保留原牌重试")
        return result(reading, sources, options.include_sources)
    finally:
        model_slots.release()
