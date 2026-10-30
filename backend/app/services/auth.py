# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import AuthSession, User

hasher = PasswordHasher()  # Argon2id, library's reviewed default parameters.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def register(session, credentials):
    user = User(email=credentials.email, password_hash=hasher.hash(credentials.password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(400, "无法注册，请检查信息或使用其他凭证") from None
    return user


def login(session, credentials):
    user = session.scalar(select(User).where(User.email == credentials.email))
    try:
        valid = hasher.verify(user.password_hash if user else DUMMY_HASH, credentials.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or user is None or not user.is_active:
        raise HTTPException(401, "邮箱或密码无效", headers={"WWW-Authenticate": "Bearer"})
    token = secrets.token_urlsafe(32)
    expires = settings.access_token_expire_minutes * 60
    session.execute(delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC)))
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=digest(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires),
        )
    )
    session.commit()
    return {"access_token": token, "token_type": "bearer", "expires_in": expires}


def authenticate(session, token):
    user = session.scalar(
        select(User)
        .join(AuthSession)
        .where(
            AuthSession.token_hash == digest(token),
            AuthSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(401, "请登录或重新登录", headers={"WWW-Authenticate": "Bearer"})
    return user


def logout(session, token):
    session.execute(delete(AuthSession).where(AuthSession.token_hash == digest(token)))
    session.commit()
