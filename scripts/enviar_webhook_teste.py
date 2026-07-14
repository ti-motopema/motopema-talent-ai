"""Envia um webhook de teste assinado para o serviço local.

Uso:
    python3 scripts/enviar_webhook_teste.py
Requer o serviço rodando em http://localhost:8000 e o mesmo WEBHOOK_SECRET do .env.
"""

import hashlib
import hmac
import json
import os
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
SECRET = os.environ.get("WEBHOOK_SECRET", "troque-este-segredo")

payload = {
    "event_id": "evt-teste-001",
    "event_type": "pedido.criado",
    "data": {"pedido_id": 123, "valor": 99.9},
}

body = json.dumps(payload).encode("utf-8")
signature = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

request = urllib.request.Request(
    f"{BASE_URL}/webhooks/exemplo",
    data=body,
    headers={"Content-Type": "application/json", "X-Signature": signature},
    method="POST",
)

with urllib.request.urlopen(request) as response:
    print(response.status, response.read().decode())
