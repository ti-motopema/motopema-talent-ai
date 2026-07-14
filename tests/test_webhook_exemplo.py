"""Testes do webhook de exemplo: assinatura, schema e fluxo feliz."""

import json

from app.security import compute_hmac_sha256
from fastapi.testclient import TestClient

from tests.conftest import TEST_SECRET


def _payload_valido() -> dict:
    return {
        "event_id": "evt-001",
        "event_type": "pedido.criado",
        "data": {"pedido_id": 123, "valor": 99.9},
    }


def _post_assinado(client: TestClient, payload: dict, secret: str = TEST_SECRET):
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + compute_hmac_sha256(secret, body)
    return client.post(
        "/webhooks/exemplo",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )


def test_webhook_aceita_payload_valido_assinado(client: TestClient) -> None:
    response = _post_assinado(client, _payload_valido())
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_id"] == "evt-001"


def test_webhook_rejeita_assinatura_invalida(client: TestClient) -> None:
    response = _post_assinado(client, _payload_valido(), secret="segredo-errado")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_signature"


def test_webhook_rejeita_sem_assinatura(client: TestClient) -> None:
    response = client.post("/webhooks/exemplo", json=_payload_valido())
    assert response.status_code == 401


def test_webhook_rejeita_payload_invalido(client: TestClient) -> None:
    payload = {"event_type": "pedido.criado"}  # falta event_id
    response = _post_assinado(client, payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"


def test_webhook_sem_secret_aceita_sem_assinatura(client_sem_secret: TestClient) -> None:
    response = client_sem_secret.post("/webhooks/exemplo", json=_payload_valido())
    assert response.status_code == 202
