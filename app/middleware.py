"""Middlewares transversais: correlação de requisições e log de acesso."""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_logger, request_id_var

logger = get_logger("app.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Atribui um request_id a cada requisição e loga método, rota, status e duração.

    O request_id é propagado via ContextVar para todos os logs emitidos
    durante o ciclo da requisição e devolvido no header X-Request-ID.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        # Reatribui o contexto só para o log final (o reset acima evita vazamento entre requisições)
        request_id_var.set(request_id)
        logger.info(
            "requisição concluída",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        request_id_var.set(None)

        response.headers["X-Request-ID"] = request_id
        return response
