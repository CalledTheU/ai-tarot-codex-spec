# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

"""Fence stale model completions after a crashed worker is retried."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("readings", sa.Column("active_run_id", sa.Uuid(), nullable=True))


def downgrade():
    op.drop_column("readings", "active_run_id")
