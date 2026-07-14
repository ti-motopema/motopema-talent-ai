"""Hierarquia de exceções da aplicação e tratamento centralizado.

Regra: código de domínio (services) lança exceções de `AppError`;
os handlers registrados aqui convertem tudo em respostas JSON padronizadas.
Nenhum endpoint precisa de try/except para erros conhecidos.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Erro base da aplicação. Subclasses definem status e código próprios."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str = "Erro interno.",
        *,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidSignatureError(AppError):
    """Assinatura HMAC ausente ou inválida no webhook recebido."""

    status_code = 401
    error_code = "invalid_signature"


class PayloadValidationError(AppError):
    """Payload recebido não corresponde ao schema esperado."""

    status_code = 422
    error_code = "invalid_payload"


class ExternalServiceError(AppError):
    """Falha ao comunicar com um serviço externo (API de terceiros, etc.)."""

    status_code = 502
    error_code = "external_service_error"


def _error_response(
    status_code: int, error_code: str, message: str, details: Any | None = None
) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": error_code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os handlers globais de exceção na aplicação."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "erro de aplicação",
            extra={
                "extra_data": {
                    "error_code": exc.error_code,
                    "status_code": exc.status_code,
                    "path": request.url.path,
                    "detail": exc.message,
                }
            },
        )
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Erros não previstos: loga stack trace completo, mas não vaza detalhes ao cliente
        logger.exception(
            "erro não tratado",
            extra={"extra_data": {"path": request.url.path}},
        )
        return _error_response(500, "internal_error", "Erro interno inesperado.")
