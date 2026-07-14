"""Endpoints de saúde — usados por load balancers, Docker e orquestradores."""

from fastapi import APIRouter

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: o processo está de pé e respondendo."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness: pronto para receber tráfego.

    Ao adicionar dependências (banco, Redis, APIs externas),
    verifique-as aqui antes de responder "ready".
    """
    settings: Settings = get_settings()
    return {"status": "ready", "environment": settings.environment}
