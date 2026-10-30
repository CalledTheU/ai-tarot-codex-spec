# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

from sqlalchemy import select

from app.models import Reading, User


def lock_user(session, user_id):
    # Serializes per-user mutations, including concurrent idempotency requests.
    return session.scalar(select(User).where(User.id == user_id).with_for_update())


def owned(session, reading_id, user_id, *, lock=False):
    statement = select(Reading).where(Reading.id == reading_id, Reading.user_id == user_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return session.scalar(statement)


def by_key(session, user_id, key):
    return session.scalar(
        select(Reading).where(Reading.user_id == user_id, Reading.idempotency_key == key)
    )
