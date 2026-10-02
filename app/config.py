"""Configuração centralizada via pydantic-settings.

Todas as configurações vêm de variáveis de ambiente (ou do arquivo .env).
Nenhum outro módulo deve ler os.environ diretamente — sempre use get_settings().
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identity and environment
    app_name: str = "motopema-talent-ai"
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM — provider-agnostic
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_transcription_model: str = "gpt-4o-transcribe"

    # Prompts — paths relative to the project root
    prompt_video_path: str = "app/prompts/02-motopema-avaliacao-video.md"
    prompt_curriculo_path: str = "app/prompts/01-motopema-avaliacao-curriculo.md"
    prompt_comportamental_path: str = "app/prompts/03-motopema-perfil-comportamental.md"
    prompt_consolidado_path: str = "app/prompts/04-motopema-avaliacao-consolidada.md"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
