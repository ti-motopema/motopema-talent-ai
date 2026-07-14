"""Configuração centralizada e desacoplada da aplicação.

Todas as configurações vêm de variáveis de ambiente (ou do arquivo .env),
validadas e tipadas via pydantic-settings. Nenhum outro módulo deve ler
os.environ diretamente — sempre importe `get_settings()`.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, carregadas do ambiente/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identidade e ambiente
    app_name: str = "webhook-service"
    environment: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Segurança
    # Segredo para validação HMAC-SHA256 das assinaturas dos webhooks.
    # Se None/vazio, a validação é desativada (uso apenas em desenvolvimento).
    webhook_secret: str | None = None

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única (cacheada) de Settings."""
    return Settings()
