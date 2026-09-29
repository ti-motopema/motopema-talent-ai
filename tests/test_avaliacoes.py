"""Testes do recurso POST /api/v1/evaluations."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture()
def client_evaluation(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("LLM_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


def _mock_openai(result: dict | str = "Test analysis."):
    return patch(
        "app.routers.avaliacoes.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=result,
    )


_URL = "/api/v1/evaluations/video"


def test_create_evaluation_returns_201(client_evaluation: TestClient) -> None:
    with _mock_openai({"resultado_final": {"nota_final": 4.2}}):
        response = client_evaluation.post(
            _URL,
            files={"file": ("candidato.mp4", BytesIO(b"fake-video"), "video/mp4")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "candidato.mp4"
    assert body["mime_type"] == "video/mp4"
    assert body["size_bytes"] == len(b"fake-video")
    assert body["evaluation"]["resultado_final"]["nota_final"] == 4.2


def test_accepts_custom_prompt(client_evaluation: TestClient) -> None:
    with _mock_openai("custom result"):
        response = client_evaluation.post(
            _URL,
            data={"prompt": "Foque apenas na oratória."},
            files={"file": ("video.mp4", BytesIO(b"video"), "video/mp4")},
        )

    assert response.status_code == 201


def test_detects_mime_from_extension(client_evaluation: TestClient) -> None:
    with _mock_openai():
        response = client_evaluation.post(
            _URL,
            files={"file": ("clip.mov", BytesIO(b"video"), "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json()["mime_type"] == "video/quicktime"


def test_rejects_empty_file(client_evaluation: TestClient) -> None:
    with _mock_openai():
        response = client_evaluation.post(
            _URL,
            files={"file": ("empty.mp4", BytesIO(b""), "video/mp4")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"
