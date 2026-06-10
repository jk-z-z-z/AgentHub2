from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _login(client: TestClient, *, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_groups_messages_and_members_are_limited_to_current_user() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner_headers = _login(client, email="admin@example.com", password="admin123456")
        create_group = client.post(
            "/api/v1/groups",
            headers=owner_headers,
            json={
                "name": "owner-only-group",
                "description": "",
                "type": "project",
                "users": [],
                "agents": [],
            },
        )
        assert create_group.status_code == 200
        group_id = str(create_group.json()["data"]["id"])

        register = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"visibility-{suffix}@example.com",
                "username": f"visibility_{suffix}",
                "password": "secret123",
                "display_name": "Visibility User",
            },
        )
        assert register.status_code == 200
        outsider_token = register.json()["data"]["access_token"]
        outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

        list_groups_response = client.get("/api/v1/groups", headers=outsider_headers)
        assert list_groups_response.status_code == 200
        group_ids = [str(item["id"]) for item in list_groups_response.json()["data"]]
        assert group_id not in group_ids

        members_response = client.get(f"/api/v1/members?group_id={group_id}", headers=outsider_headers)
        assert members_response.status_code == 403
        assert members_response.json()["detail"] == "Forbidden"

        messages_response = client.get(f"/api/v1/messages?group_id={group_id}&limit=50", headers=outsider_headers)
        assert messages_response.status_code == 403
        assert messages_response.json()["detail"] == "Forbidden"
