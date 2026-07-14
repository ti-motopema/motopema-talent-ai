"""Regra de negócio do webhook de exemplo.

Services concentram a lógica de domínio e integrações. Não conhecem HTTP,
headers nem FastAPI — recebem objetos já validados (schemas) e retornam
resultados ou lançam exceções de app.exceptions.
"""

from app.logging_config import get_logger
from app.schemas.exemplo import ExemploEvent

logger = get_logger(__name__)


class ExemploService:
    """Processa eventos do webhook de exemplo."""

    def process(self, evento: ExemploEvent) -> None:
        """Processa um evento em background.

        Substitua o corpo deste método pela regra de negócio real:
        gravar no banco, chamar APIs externas (via httpx), enfileirar, etc.
        """
        logger.info(
            "processando evento",
            extra={
                "extra_data": {
                    "event_id": evento.event_id,
                    "event_type": evento.event_type,
                }
            },
        )

        # >>> Regra de negócio entra aqui <<<

        logger.info(
            "evento processado com sucesso",
            extra={"extra_data": {"event_id": evento.event_id}},
        )
