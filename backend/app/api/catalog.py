# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.catalog_data import CardData, Position
from app.database import get_session
from app.repositories.catalog import list_spreads
from app.services import catalog

router = APIRouter(prefix="/api/v1", tags=["catalog"])


class CardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    name_zh: str
    name_en: str
    arcana_type: Literal["major", "minor"]
    suit: Literal["wands", "cups", "swords", "pentacles"] | None
    rank: str
    upright_keywords: list[str]
    reversed_keywords: list[str]
    image_path: str | None


class CardPage(BaseModel):
    items: list[CardSummary]
    total: int
    page: int
    page_size: int


class SpreadView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    name: str
    description: str
    positions: list[Position] = Field(min_length=1)
    version: str


@router.get("/cards", response_model=CardPage)
def cards(
    page: int = Query(1, ge=1, le=2147483647),
    page_size: int = Query(20, ge=1, le=100),
    arcana_type: Literal["major", "minor"] | None = None,
    suit: Literal["wands", "cups", "swords", "pentacles"] | None = None,
    q: str = Query("", max_length=100),
    session: Session = Depends(get_session),
):
    return catalog.list_cards(session, page, page_size, arcana_type, suit, q)


@router.get("/cards/{identifier}", response_model=CardData)
def card(identifier: str, session: Session = Depends(get_session)):
    return catalog.get_card(session, identifier)


@router.get("/spreads", response_model=list[SpreadView])
def spreads(session: Session = Depends(get_session)):
    return list_spreads(session)


@router.get("/spreads/{identifier}", response_model=SpreadView)
def spread(identifier: str, session: Session = Depends(get_session)):
    return catalog.get_spread(session, identifier)
