from fastapi.testclient import TestClient

from agenthub_backend.main import app


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
