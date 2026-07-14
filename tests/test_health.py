"""Testes dos endpoints de saúde."""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_request_id_no_header(client: TestClient) -> None:
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
