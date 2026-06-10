from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_register_returns_access_token_and_user_defaults() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"register-{suffix}@example.com",
                "username": f"register_{suffix}",
                "display_name": "New User",
                "password": "secret123",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["user"]["email"] == f"register-{suffix}@example.com"
    assert data["user"]["username"] == f"register_{suffix}"
    assert data["user"]["display_name"] == "New User"
    assert data["user"]["role"] == "user"
    assert data["user"]["status"] == "active"
    assert data["user"]["bio"] == ""


def test_register_rejects_duplicate_email_or_username() -> None:
    suffix = uuid4().hex[:8]
    payload = {
        "email": f"duplicate-{suffix}@example.com",
        "username": f"duplicate_{suffix}",
        "password": "secret123",
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/auth/register", json=payload)
        second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "email or username already exists"


def test_create_user_uses_request_defaults() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": f"create-{suffix}@example.com",
                "username": f"create_{suffix}",
                "password": "secret123",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["role"] == "user"
    assert data["status"] == "active"
    assert data["bio"] == ""
    assert data["display_name"] is None
