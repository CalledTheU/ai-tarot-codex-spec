# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models import Spread, TarotCard


def list_cards(session: Session, page, page_size, arcana_type=None, suit=None, q=""):
    filters = []
    if arcana_type:
        filters.append(TarotCard.arcana_type == arcana_type)
    if suit:
        filters.append(TarotCard.suit == suit)
    if q:
        filters.append(
            or_(
                TarotCard.name_zh.icontains(q, autoescape=True),
                TarotCard.name_en.icontains(q, autoescape=True),
            )
        )
    total = session.scalar(select(func.count()).select_from(TarotCard).where(*filters))
    ranks = [str(i) for i in range(22)] + [
        "ace",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "page",
        "knight",
        "queen",
        "king",
    ]
    statement = (
        select(TarotCard)
        .where(*filters)
        .order_by(
            TarotCard.arcana_type,
            TarotCard.suit,
            case({rank: i for i, rank in enumerate(ranks)}, value=TarotCard.rank, else_=100),
            TarotCard.slug,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement)), total


def get_by_id_or_slug(session: Session, model, identifier: str, *, active_only=False):
    try:
        resource_id = UUID(identifier)
    except ValueError:
        condition = model.slug == identifier
    else:
        condition = or_(model.id == resource_id, model.slug == identifier)
    statement = select(model).where(condition)
    if active_only:
        statement = statement.where(model.is_active.is_(True))
    return session.scalar(statement)


def list_spreads(session: Session):
    return list(
        session.scalars(select(Spread).where(Spread.is_active.is_(True)).order_by(Spread.slug))
    )
