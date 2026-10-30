# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.api.auth import current_user
from app.database import get_session
from app.llm import ModelAdapter, get_model
from app.schemas import CreateReading, InterpretRequest, InterpretView, ReadingView
from app.services import readings
from app.services.interpretation import interpret

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])


@router.post("", status_code=201, response_model=ReadingView)
def create(
    data: CreateReading,
    response: Response,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    ],
    user=Depends(current_user),
    session: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return readings.create(session, user, data, idempotency_key)


@router.get("/{reading_id}", response_model=ReadingView)
def detail(
    reading_id: UUID,
    response: Response,
    user=Depends(current_user),
    session: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return readings.view(readings.require_owned(session, reading_id, user.id))


@router.post("/{reading_id}/interpret", response_model=InterpretView)
async def interpretation(
    reading_id: UUID,
    data: InterpretRequest,
    response: Response,
    user=Depends(current_user),
    session: Session = Depends(get_session),
    model: ModelAdapter = Depends(get_model),
):
    response.headers["Cache-Control"] = "no-store"
    return await interpret(session, user, reading_id, data, model)
