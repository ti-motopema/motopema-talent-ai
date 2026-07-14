"""Fixtures compartilhadas dos testes."""

import os

import pytest
from app.config import get_settings
from fastapi.testclient import TestClient

TEST_SECRET = "segredo-de-teste"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente HTTP de teste com WEBHOOK_SECRET conhecido."""
    monkeypatch.setenv("WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setenv("ENVIRONMENT", "dev")
    get_settings.cache_clear()  # força releitura das variáveis de ambiente

    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


@pytest.fixture()
def client_sem_secret(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente sem segredo configurado (validação de assinatura desativada)."""
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    os.environ.pop("WEBHOOK_SECRET", None)
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
