# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.readings import router as readings_router
from app.database import get_session
from app.services.catalog import CatalogNotFound

app = FastAPI(title="AI Tarot API")
app.include_router(catalog_router)
app.include_router(auth_router)
app.include_router(readings_router)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    if request.url.path.startswith(("/api/v1/auth", "/api/v1/readings")):
        response.headers["Cache-Control"] = "no-store"
    return response


def error_response(request: Request, status_code: int, code: str, message: str, headers=None):
    return JSONResponse(
        status_code=status_code,
        headers={**(headers or {}), "X-Request-ID": request.state.request_id},
        content={
            "error": {"code": code, "message": message, "request_id": request.state.request_id}
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    codes = {
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "INVALID_STATE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "MODEL_UNAVAILABLE",
        503: "MODEL_UNAVAILABLE",
    }
    return error_response(
        request,
        exc.status_code,
        codes.get(exc.status_code, "HTTP_ERROR"),
        "服务暂时不可用" if exc.status_code >= 500 else str(exc.detail),
        exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error_response(request, 422, "VALIDATION_ERROR", "请求参数无效")


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    return error_response(request, 500, "INTERNAL_ERROR", "服务器内部错误")


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return error_response(request, 503, "DATABASE_UNAVAILABLE", "数据库暂时不可用")


@app.exception_handler(CatalogNotFound)
async def catalog_not_found(request: Request, exc: CatalogNotFound):
    return error_response(request, 404, "NOT_FOUND", str(exc))


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
