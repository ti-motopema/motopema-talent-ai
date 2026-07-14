"""Ponto de entrada da aplicação — fábrica do FastAPI (app factory).

O padrão create_app() permite criar instâncias configuradas sob demanda
(útil para testes) e mantém o wiring da aplicação em um único lugar.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.logging_config import get_logger, setup_logging
from app.middleware import RequestContextMiddleware
from app.routers import health
from app.routers.webhooks import exemplo

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicialização e finalização de recursos (conexões, clients, etc.)."""
    settings = get_settings()
    logger.info(
        "aplicação iniciada",
        extra={"extra_data": {"app": settings.app_name, "env": settings.environment}},
    )
    yield
    logger.info("aplicação finalizada")


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        # Em produção, desative a documentação pública se o serviço for exposto
        docs_url="/docs" if not settings.is_prod else None,
        redoc_url=None,
    )

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(exemplo.router)

    return app


app = create_app()
