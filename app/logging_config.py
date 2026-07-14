"""Logging estruturado em JSON, com correlação por request_id.

Cada linha de log é um JSON — pronto para ingestão em ferramentas como
Loki, CloudWatch, Datadog ou simples `grep`/`jq` em arquivos.

Uso:
    logger = get_logger(__name__)
    logger.info("evento processado", extra={"extra_data": {"event_id": "123"}})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# request_id propagado por contexto (setado pelo middleware a cada requisição)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Serializa cada registro de log como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Campos adicionais passados via extra={"extra_data": {...}}
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            payload.update(extra_data)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configura o logger raiz com saída JSON em stdout (12-factor)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # O access log do uvicorn é redundante: o middleware já loga cada requisição
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Atalho padronizado para obter loggers por módulo."""
    return logging.getLogger(name)
