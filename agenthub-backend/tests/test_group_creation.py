from fastapi.testclient import TestClient

from app.main import app


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123456"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_project_group_ignores_duplicate_creator_member() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client)
        response = client.post(
            "/api/v1/groups",
            headers=headers,
            json={
                "name": "creator-duplicate-project",
                "description": "",
                "type": "project",
                "users": [
                    {
                        "user_id": "1",
                        "display_name": "管理员",
                        "title": None,
                    }
                ],
                "agents": [],
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["type"] == "project"
        assert data["workspace_id"]
