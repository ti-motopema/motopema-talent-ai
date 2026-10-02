"""Fixtures compartilhadas dos testes."""

import pytest
from app.config import get_settings
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
