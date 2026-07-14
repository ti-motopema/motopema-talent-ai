"""Verificação de assinatura de webhooks (HMAC-SHA256).

Padrão adotado pela maioria dos provedores (GitHub, Meta, Stripe com variações):
o emissor assina o corpo bruto da requisição com um segredo compartilhado e
envia o resultado em um header. Aqui validamos com comparação em tempo constante.
"""

import hashlib
import hmac


def compute_hmac_sha256(secret: str, payload: bytes) -> str:
    """Calcula a assinatura HMAC-SHA256 (hex) de um payload."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_hmac_sha256(secret: str, payload: bytes, signature: str) -> bool:
    """Valida a assinatura recebida contra o payload bruto.

    Aceita tanto o formato "sha256=<hex>" (estilo GitHub/Meta) quanto o hex puro.
    Usa hmac.compare_digest para evitar timing attacks.
    """
    provided = signature.strip().removeprefix("sha256=")
    expected = compute_hmac_sha256(secret, payload)
    return hmac.compare_digest(expected, provided)
