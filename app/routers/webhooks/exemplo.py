"""Webhook de exemplo — modelo a ser copiado para novos webhooks.

Fluxo padrão de um webhook neste template:
1. Lê o corpo BRUTO da requisição (necessário para validar a assinatura).
2. Valida a assinatura HMAC (se WEBHOOK_SECRET estiver configurado).
3. Valida o payload contra o schema Pydantic.
4. Responde 202 imediatamente e processa em background.
   (Provedores de webhook esperam resposta rápida; processamento pesado
   nunca deve bloquear a resposta.)
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.exceptions import InvalidSignatureError, PayloadValidationError
from app.logging_config import get_logger
from app.schemas.exemplo import ExemploEvent
from app.security import verify_hmac_sha256
from app.services.exemplo_service import ExemploService

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_exemplo_service() -> ExemploService:
    """Fábrica do service (facilita substituição/mocking em testes)."""
    return ExemploService()


@router.post("/exemplo", status_code=202)
async def receber_webhook_exemplo(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    service: ExemploService = Depends(get_exemplo_service),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict[str, Any]:
    raw_body = await request.body()

    # 1) Assinatura
    if settings.webhook_secret:
        if not x_signature or not verify_hmac_sha256(
            settings.webhook_secret, raw_body, x_signature
        ):
            raise InvalidSignatureError("Assinatura do webhook ausente ou inválida.")
    else:
        logger.warning("WEBHOOK_SECRET não configurado — validação de assinatura desativada")

    # 2) Schema
    try:
        evento = ExemploEvent.model_validate_json(raw_body)
    except ValidationError as exc:
        raise PayloadValidationError(
            "Payload inválido para o webhook 'exemplo'.",
            details=exc.errors(include_url=False),
        ) from exc

    logger.info(
        "webhook recebido",
        extra={"extra_data": {"webhook": "exemplo", "event_id": evento.event_id}},
    )

    # 3) Ack rápido + processamento assíncrono
    background_tasks.add_task(service.process, evento)

    return {"status": "accepted", "event_id": evento.event_id}
