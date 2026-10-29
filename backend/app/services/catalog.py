# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from app.models import Spread, TarotCard
from app.repositories import catalog


class CatalogNotFound(Exception):
    pass


def list_cards(session, page, page_size, arcana_type, suit, q):
    items, total = catalog.list_cards(session, page, page_size, arcana_type, suit, q.strip())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_card(session, identifier):
    card = catalog.get_by_id_or_slug(session, TarotCard, identifier)
    if card is None:
        raise CatalogNotFound("未找到这张牌")
    return card


def get_spread(session, identifier):
    spread = catalog.get_by_id_or_slug(session, Spread, identifier, active_only=True)
    if spread is None:
        raise CatalogNotFound("未找到这个牌阵")
    return spread
