# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def error_client(monkeypatch):
    monkeypatch.setattr(app.router, "routes", list(app.router.routes))

    @app.get("/test/validation")
    def validation(value: int):
        return {"value": value}

    @app.get("/test/internal")
    def internal():
        raise RuntimeError("private database connection details")

    @app.get("/test/http-error")
    def http_error(status: int):
        raise HTTPException(
            status_code=status,
            detail="private upstream details" if status >= 500 else "Request rejected",
            headers={"Retry-After": "30"},
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/test/validation?value=private-input", 422, "VALIDATION_ERROR"),
        ("/test/internal", 500, "INTERNAL_ERROR"),
        ("/test/http-error?status=429", 429, "RATE_LIMITED"),
        ("/test/http-error?status=503", 503, "MODEL_UNAVAILABLE"),
    ],
)
def test_error_paths(error_client, path, status, code):
    response = error_client.get(path)
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert "private" not in response.text
    if path.startswith("/test/http-error"):
        assert response.headers["Retry-After"] == "30"


def test_health_and_error_contract(database_app):
    with TestClient(app) as client:
        for path in ("/health/live", "/health/ready"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert response.headers["X-Request-ID"]

        response = client.get("/missing")
        assert response.status_code == 404
        assert response.json() == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Not Found",
                "request_id": response.headers["X-Request-ID"],
            }
        }
