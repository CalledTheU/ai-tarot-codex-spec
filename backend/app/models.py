# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


json_type = JSON().with_variant(JSONB(), "postgresql")


class Identity:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class User(Identity, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(trim(email))", name="normalized_email"),)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class AuthSession(Identity, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class TarotCard(Identity, Timestamps, Base):
    __tablename__ = "tarot_cards"
    __table_args__ = (
        CheckConstraint(
            "(arcana_type = 'major' AND suit IS NULL) OR "
            "(arcana_type = 'minor' AND suit IS NOT NULL)",
            name="arcana_suit",
        ),
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name_zh: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    arcana_type: Mapped[str] = mapped_column(
        Enum("major", "minor", name="arcana_type", native_enum=False, create_constraint=True)
    )
    suit: Mapped[str | None] = mapped_column(
        Enum(
            "wands",
            "cups",
            "swords",
            "pentacles",
            name="suit",
            native_enum=False,
            create_constraint=True,
        )
    )
    rank: Mapped[str] = mapped_column(String(20))
    upright_keywords: Mapped[list] = mapped_column(json_type)
    reversed_keywords: Mapped[list] = mapped_column(json_type)
    upright_meaning: Mapped[str] = mapped_column(Text)
    reversed_meaning: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[dict] = mapped_column(json_type)
    content_version: Mapped[str] = mapped_column(String(40))


class Spread(Identity, Timestamps, Base):
    __tablename__ = "spreads"
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    positions: Mapped[list] = mapped_column(json_type)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    version: Mapped[str] = mapped_column(String(40))


class Reading(Identity, Timestamps, Base):
    __tablename__ = "readings"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    draw_metadata: Mapped[dict | None] = mapped_column(json_type)
    active_run_id: Mapped[UUID | None] = mapped_column(Uuid)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    spread_id: Mapped[UUID] = mapped_column(ForeignKey("spreads.id"))
    spread_snapshot: Mapped[dict] = mapped_column(json_type)
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        Enum(
            "love",
            "relationship",
            "career",
            "study",
            "growth",
            "other",
            name="category",
            native_enum=False,
            create_constraint=True,
        )
    )
    background: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending_interpretation",
            "processing",
            "completed",
            "failed",
            name="reading_status",
            native_enum=False,
            create_constraint=True,
        )
    )
    cards_snapshot: Mapped[list] = mapped_column(json_type)
    interpretation: Mapped[dict | None] = mapped_column(json_type)
    interpretation_version: Mapped[str | None] = mapped_column(String(40))


class ReadingCard(Identity, Base):
    __tablename__ = "reading_cards"
    __table_args__ = (
        UniqueConstraint("reading_id", "card_id"),
        UniqueConstraint("reading_id", "position_index"),
        CheckConstraint("position_index >= 0", name="nonnegative_position"),
    )
    reading_id: Mapped[UUID] = mapped_column(
        ForeignKey("readings.id", ondelete="CASCADE"), index=True
    )
    card_id: Mapped[UUID] = mapped_column(ForeignKey("tarot_cards.id"))
    position_index: Mapped[int] = mapped_column(Integer)
    position_name: Mapped[str] = mapped_column(String(100))
    orientation: Mapped[str] = mapped_column(
        Enum("upright", "reversed", name="orientation", native_enum=False, create_constraint=True)
    )
    card_snapshot: Mapped[dict] = mapped_column(json_type)


class ChatMessage(Identity, Base):
    __tablename__ = "chat_messages"
    reading_id: Mapped[UUID] = mapped_column(
        ForeignKey("readings.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", name="chat_role", native_enum=False, create_constraint=True)
    )
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(json_type, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Identity, Base):
    __tablename__ = "agent_runs"
    reading_id: Mapped[UUID] = mapped_column(
        ForeignKey("readings.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "running",
            "completed",
            "failed",
            name="run_status",
            native_enum=False,
            create_constraint=True,
        )
    )
    provider: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    diagnostics: Mapped[dict] = mapped_column(json_type, default=dict, server_default="{}")
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
