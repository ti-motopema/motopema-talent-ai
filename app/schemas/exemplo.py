"""Schemas (contratos de dados) do webhook de exemplo.

Cada webhook deve ter seus schemas próprios neste pacote — o schema é o
contrato entre o provedor externo e a aplicação, e a validação Pydantic
garante que dados malformados nunca cheguem à camada de serviço.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExemploEvent(BaseModel):
    """Evento genérico recebido pelo webhook de exemplo."""

    event_id: str = Field(..., min_length=1, description="Identificador único do evento")
    event_type: str = Field(..., min_length=1, description="Tipo do evento (ex.: 'pedido.criado')")
    timestamp: datetime | None = Field(default=None, description="Momento do evento na origem")
    data: dict[str, Any] = Field(default_factory=dict, description="Carga útil do evento")
