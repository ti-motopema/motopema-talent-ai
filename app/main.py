"""Ponto de entrada da aplicação — fábrica do FastAPI (app factory)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.logging_config import get_logger, setup_logging
from app.middleware import RequestContextMiddleware
from app.routers import avaliacoes, health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info(
        "application started",
        extra={"extra_data": {"app": settings.app_name, "env": settings.environment}},
    )
    yield
    logger.info("application stopped")


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_prod else None,
        redoc_url=None,
    )

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    # Infrastructure — unversioned
    app.include_router(health.router)

    # Business API — versioned
    app.include_router(avaliacoes.router, prefix="/api/v1")

    return app


app = create_app()
