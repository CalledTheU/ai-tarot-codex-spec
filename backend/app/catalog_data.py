# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SUITS = ("wands", "cups", "swords", "pentacles")
RANKS = {
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
}


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    title: str
    author: str
    publication_year: int
    url: HttpUrl
    reversed_url: HttpUrl | None = None
    locator: str
    license: str
    language: Literal["en"]
    content_kind: Literal["historical_excerpt"]
    review_status: Literal["source_verified_not_modern_advice"]
    retrieved_on: str
    version: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    excerpt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CardData(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    slug: str = Field(min_length=1)
    name_zh: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    arcana_type: Literal["major", "minor"]
    suit: Literal["wands", "cups", "swords", "pentacles"] | None
    rank: str
    upright_keywords: list[str] = Field(min_length=1)
    reversed_keywords: list[str] = Field(min_length=1)
    upright_meaning: str = Field(min_length=1)
    reversed_meaning: str = Field(min_length=1)
    image_path: str | None
    source_reference: SourceReference
    content_version: str

    @model_validator(mode="after")
    def check_integrity(self):
        if (self.arcana_type == "major") != (self.suit is None):
            raise ValueError("Arcana and suit do not match")
        digest = hashlib.sha256(
            (self.upright_meaning + "\n" + self.reversed_meaning).encode()
        ).hexdigest()
        if digest != self.source_reference.excerpt_sha256:
            raise ValueError("Excerpt hash does not match")
        return self


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class SpreadData(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    positions: list[Position] = Field(min_length=1)
    is_active: bool
    version: str

    @model_validator(mode="after")
    def check_positions(self):
        if [p.index for p in self.positions] != list(range(len(self.positions))):
            raise ValueError("Positions must have consecutive unique indices from zero")
        return self


def load_seed_data(directory: Path | None = None):
    directory = directory or Path(__file__).parent / "data"
    cards = [
        CardData.model_validate(row)
        for row in json.loads((directory / "cards.json").read_text(encoding="utf-8"))
    ]
    spreads = [
        SpreadData.model_validate(row)
        for row in json.loads((directory / "spreads.json").read_text(encoding="utf-8"))
    ]
    if len(cards) != 78 or Counter(c.arcana_type for c in cards) != {"major": 22, "minor": 56}:
        raise ValueError("Catalog must contain 22 major and 56 minor cards")
    if {c.rank for c in cards if c.arcana_type == "major"} != {str(i) for i in range(22)}:
        raise ValueError("Major ranks must cover zero through 21")
    for suit in SUITS:
        suited = [c for c in cards if c.suit == suit]
        if len(suited) != 14 or {c.rank for c in suited} != RANKS:
            raise ValueError("Each suit must contain all 14 ranks")
    for rows in (cards, spreads):
        if len({r.id for r in rows}) != len(rows) or len({r.slug for r in rows}) != len(rows):
            raise ValueError("Seed IDs and slugs must be unique")
    if {s.slug: len(s.positions) for s in spreads} != {
        "single-card": 1,
        "three-card-past-present-future": 3,
        "three-card-situation-challenge-advice": 3,
        "five-card-reflection": 5,
    }:
        raise ValueError("Expected four initial spreads with 1/3/3/5 positions")
    return cards, spreads
