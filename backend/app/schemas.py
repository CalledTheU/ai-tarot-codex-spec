# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Category = Literal["love", "relationship", "career", "study", "growth", "other"]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(StrictInput):
    email: str = Field(min_length=3, max_length=320)
    # Passwords retain whitespace; normalization must never change a password.
    password: Annotated[
        str, StringConstraints(strip_whitespace=False, min_length=12, max_length=128)
    ]

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        return value


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str


class LoginView(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class CreateReading(StrictInput):
    question: str = Field(min_length=1, max_length=1000)
    background: str | None = Field(default=None, max_length=5000)
    category: Category
    spread_id: str = Field(min_length=1, max_length=100)


class ReadingView(BaseModel):
    id: UUID
    status: Literal["pending_interpretation", "processing", "completed", "failed"]
    question: str
    category: Category
    background: str | None
    spread: dict
    cards: list[dict]
    draw_metadata: dict | None
    interpretation: dict | None
    created_at: datetime


class InterpretRequest(StrictInput):
    style: Literal["concise", "detailed"] = "detailed"
    include_sources: bool = True


Nonempty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]


class CardInterpretation(StrictInput):
    card_id: UUID
    position_index: int = Field(ge=0, strict=True)
    position_name: Nonempty
    orientation: Literal["upright", "reversed"]
    traditional_meaning: Nonempty
    contextual_interpretation: Nonempty
    source_ids: list[Nonempty] = Field(min_length=1, max_length=5)


class Scenario(StrictInput):
    description: Nonempty
    basis: Nonempty


class Interpretation(StrictInput):
    summary: Nonempty
    scope_note: Nonempty
    card_interpretations: list[CardInterpretation] = Field(min_length=1, max_length=78)
    synthesis: Nonempty
    possible_scenarios: list[Scenario] = Field(min_length=1, max_length=10)
    action_suggestions: list[Nonempty] = Field(min_length=1, max_length=10)
    reflection_questions: list[Nonempty] = Field(min_length=1, max_length=10)
    uncertainties: list[Nonempty] = Field(min_length=1, max_length=10)


class InterpretView(BaseModel):
    reading_id: UUID
    status: Literal["completed"] = "completed"
    interpretation: Interpretation
    sources: list[dict]
    run_id: UUID
