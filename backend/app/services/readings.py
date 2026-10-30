# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.catalog_data import CardData, Position, SpreadData
from app.config import settings
from app.models import Reading, ReadingCard, TarotCard
from app.repositories import readings as repository
from app.services.catalog import get_spread


def require_owned(session, reading_id, user_id, *, lock=False):
    reading = repository.owned(session, reading_id, user_id, lock=lock)
    if reading is None:
        raise HTTPException(404, "未找到记录")
    return reading


def view(reading):
    return {
        "id": reading.id,
        "status": reading.status,
        "question": reading.question,
        "category": reading.category,
        "background": reading.background,
        "spread": reading.spread_snapshot,
        "cards": reading.cards_snapshot,
        "draw_metadata": reading.draw_metadata,
        "interpretation": reading.interpretation,
        "created_at": reading.created_at,
    }


def replay(existing, request_hash):
    if existing.request_hash != request_hash:
        raise HTTPException(409, "同一幂等键不能用于不同的请求")
    return view(existing)


def create(session, user, data, key):
    request_hash = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    repository.lock_user(session, user.id)
    existing = repository.by_key(session, user.id, key)
    if existing:
        return replay(existing, request_hash)
    recent = session.scalar(
        select(func.count())
        .select_from(Reading)
        .where(
            Reading.user_id == user.id,
            Reading.created_at > datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    if recent >= settings.readings_per_minute:
        raise HTTPException(429, "抽牌请求过于频繁", headers={"Retry-After": "60"})
    spread = get_spread(session, data.spread_id)
    positions = [Position.model_validate(p) for p in spread.positions]
    if not positions or sorted(p.index for p in positions) != list(range(len(positions))):
        raise HTTPException(409, "牌阵配置无效")
    deck = list(session.scalars(select(TarotCard).order_by(TarotCard.id)))
    if len(deck) != 78 or len(positions) > len(deck):
        raise HTTPException(409, "牌库尚未准备就绪")
    chosen = secrets.SystemRandom().sample(deck, len(positions))
    cards = []
    for position, card in zip(sorted(positions, key=lambda p: p.index), chosen, strict=True):
        snapshot = CardData.model_validate(card, from_attributes=True).model_dump(mode="json")
        cards.append(
            {
                "card_id": str(card.id),
                "name": card.name_zh,
                "position_index": position.index,
                "position_name": position.name,
                "orientation": "reversed" if secrets.randbelow(2) else "upright",
                "card_snapshot": snapshot,
            }
        )
    reading = Reading(
        user_id=user.id,
        spread_id=spread.id,
        spread_snapshot=SpreadData.model_validate(spread).model_dump(
            mode="json", exclude={"is_active"}
        ),
        question=data.question,
        category=data.category,
        background=data.background,
        status="pending_interpretation",
        cards_snapshot=cards,
        idempotency_key=key,
        request_hash=request_hash,
        draw_metadata={"algorithm": "secrets-sample-v1", "drawn_at": datetime.now(UTC).isoformat()},
    )
    session.add(reading)
    try:
        session.flush()
        for card in cards:
            session.add(
                ReadingCard(
                    reading_id=reading.id,
                    card_id=UUID(card["card_id"]),
                    position_index=card["position_index"],
                    position_name=card["position_name"],
                    orientation=card["orientation"],
                    card_snapshot=card["card_snapshot"],
                )
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = repository.by_key(session, user.id, key)
        if existing is None:
            raise
        return replay(existing, request_hash)
    return view(reading)
