# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-30

import time
from collections import OrderedDict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_session
from app.schemas import Credentials, LoginView, UserView
from app.services import auth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)
_attempts = OrderedDict()
_rate_lock = Lock()


def auth_limit(request: Request):
    # shortcut: per-process IP protection; use a shared proxy limiter before multiple workers.
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _rate_lock:
        start, count = _attempts.pop(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        _attempts[key] = (start, count + 1)
        if len(_attempts) > 10000:
            _attempts.popitem(last=False)
        if count >= settings.auth_requests_per_minute:
            raise HTTPException(429, "请求过于频繁，请稍后再试", headers={"Retry-After": "60"})


def get_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or len(credentials.credentials) > 512:
        raise HTTPException(401, "请登录", headers={"WWW-Authenticate": "Bearer"})
    return credentials.credentials


def current_user(token: str = Depends(get_token), session: Session = Depends(get_session)):
    return auth.authenticate(session, token)


@router.post(
    "/register", status_code=201, response_model=UserView, dependencies=[Depends(auth_limit)]
)
def register(data: Credentials, response: Response, session: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return auth.register(session, data)


@router.post("/login", response_model=LoginView, dependencies=[Depends(auth_limit)])
def login(data: Credentials, response: Response, session: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return auth.login(session, data)


@router.get("/me", response_model=UserView)
def me(response: Response, user=Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/logout", status_code=204)
def logout(token: str = Depends(get_token), session: Session = Depends(get_session)):
    auth.logout(session, token)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
