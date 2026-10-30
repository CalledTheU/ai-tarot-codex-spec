# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

"""Revocable sessions and idempotent, versioned draws."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    with op.batch_alter_table("readings") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128)))
        batch.add_column(sa.Column("request_hash", sa.String(64)))
        batch.add_column(
            sa.Column("draw_metadata", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"))
        )
        batch.create_unique_constraint(
            "uq_readings_user_id_idempotency_key", ["user_id", "idempotency_key"]
        )


def downgrade():
    with op.batch_alter_table("readings") as batch:
        batch.drop_constraint("uq_readings_user_id_idempotency_key", type_="unique")
        for column in ("draw_metadata", "request_hash", "idempotency_key"):
            batch.drop_column(column)
    op.drop_table("auth_sessions")
