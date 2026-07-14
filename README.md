# Webhook Template

Template profissional e reutilizável para serviços de **Webhooks em Python**, construído com **FastAPI**. Serve como ponto de partida padronizado para novos projetos: clone, renomeie e comece a implementar a regra de negócio.

## Por que FastAPI

- **Assíncrono nativo**: webhooks são I/O-bound (recebem HTTP, chamam APIs, gravam em banco). O modelo async do FastAPI/uvicorn atende alto volume com poucos recursos.
- **Validação automática com Pydantic**: o payload do webhook é o contrato com o mundo externo — Pydantic valida, tipa e documenta esse contrato.
- **Documentação automática**: `/docs` (Swagger) gerado a partir do código.
- **Tipagem de ponta a ponta**: integra naturalmente com `typing` e `mypy`.

## Arquitetura

```
Requisição HTTP
      │
      ▼
Middleware (request_id + log de acesso)
      │
      ▼
Router (app/routers/webhooks/…)      ← camada HTTP: assinatura, schema, ack 202
      │
      ▼
Service (app/services/…)             ← regra de negócio, sem conhecer HTTP
      │
      ▼
Integrações externas / persistência
```

Princípios aplicados:

- **Separação de responsabilidades**: routers cuidam de HTTP; services cuidam de negócio; schemas definem contratos; config e logging são transversais.
- **Ack rápido + processamento em background**: provedores de webhook exigem resposta em poucos segundos. O endpoint valida, responde `202 Accepted` e processa via `BackgroundTasks`.
- **Tratamento centralizado de exceções**: services lançam exceções de `app/exceptions.py`; handlers globais convertem em respostas JSON padronizadas. Endpoints não precisam de try/except.
- **Configuração desacoplada**: tudo vem de variáveis de ambiente via `pydantic-settings`. Nenhum módulo lê `os.environ` diretamente.
- **Logs estruturados em JSON** com `request_id` de correlação em todas as linhas.
- **Segurança**: validação de assinatura HMAC-SHA256 do corpo bruto, com comparação em tempo constante.

## Estrutura de diretórios

```
webhook-template/
├── app/
│   ├── main.py                     # App factory (create_app) e wiring geral
│   ├── config.py                   # Settings via pydantic-settings (.env)
│   ├── logging_config.py           # Logs JSON estruturados + request_id
│   ├── exceptions.py               # Hierarquia de erros + handlers globais
│   ├── middleware.py               # Request ID, timing e log de acesso
│   ├── security.py                 # Verificação de assinatura HMAC-SHA256
│   ├── routers/
│   │   ├── health.py               # /health e /ready
│   │   └── webhooks/
│   │       └── exemplo.py          # Webhook modelo (copiar para novos)
│   ├── schemas/
│   │   └── exemplo.py              # Contratos Pydantic do webhook exemplo
│   ├── services/
│   │   └── exemplo_service.py      # Regra de negócio do webhook exemplo
│   └── utils/                      # Helpers genéricos (vazio por padrão)
├── tests/
│   ├── conftest.py                 # Fixtures (TestClient com secret de teste)
│   ├── test_health.py
│   └── test_webhook_exemplo.py
├── scripts/
│   └── enviar_webhook_teste.py     # Envia um webhook assinado ao serviço local
├── .vscode/                        # Configuração do editor (ruff, mypy, pytest)
├── .env.example                    # Modelo de variáveis de ambiente
├── .gitignore
├── .pre-commit-config.yaml         # Hooks de qualidade pré-commit
├── pyproject.toml                  # Dependências + config de ruff/mypy/pytest
├── Makefile                        # Atalhos: install, run, test, lint, check…
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Dependências

| Pacote | Papel |
|---|---|
| `fastapi` | Framework web assíncrono |
| `uvicorn[standard]` | Servidor ASGI de produção |
| `pydantic` | Validação e tipagem dos payloads |
| `pydantic-settings` | Configuração tipada via `.env` |
| `httpx` | Cliente HTTP assíncrono (chamadas externas e testes) |

Desenvolvimento: `pytest` + `pytest-cov` (testes), `ruff` (lint **e** formatação — substitui flake8/black/isort), `mypy` (tipos), `pre-commit` (hooks).

## Como executar localmente

```bash
cp .env.example .env        # ajuste WEBHOOK_SECRET
make install                # cria .venv e instala dependências
make hooks                  # instala hooks de pré-commit (opcional, recomendado)
make run                    # sobe em http://localhost:8000 com reload
```

Sem Make: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/uvicorn app.main:app --reload`.

Verificação rápida:

```bash
curl http://localhost:8000/health && echo "---" && python3 scripts/enviar_webhook_teste.py
```

Documentação interativa: `http://localhost:8000/docs`.

Qualidade: `make lint`, `make format`, `make typecheck`, `make test` ou tudo de uma vez com `make check`.

Com Docker: `docker compose up --build`.

## Como adicionar um novo webhook

Exemplo: webhook `pagamento`.

1. **Schema** — crie `app/schemas/pagamento.py` com o modelo Pydantic do payload do provedor.
2. **Service** — crie `app/services/pagamento_service.py` com a classe `PagamentoService` e o método `process()`. Toda a regra de negócio vive aqui.
3. **Router** — copie `app/routers/webhooks/exemplo.py` para `pagamento.py`, ajuste o prefixo/rota, o schema e o service. O fluxo (corpo bruto → assinatura → schema → 202 + background) permanece o mesmo.
4. **Registro** — em `app/main.py`, adicione `app.include_router(pagamento.router)`.
5. **Testes** — copie `tests/test_webhook_exemplo.py` e adapte os casos (assinatura válida/inválida, payload inválido, fluxo feliz).

Se o provedor usa outro esquema de assinatura (token fixo em header, HMAC com prefixo diferente, etc.), adicione a função correspondente em `app/security.py` e use-a apenas naquele router.

## Como evoluir para projetos maiores

- **Persistência**: adicione `app/repositories/` com SQLAlchemy 2.0 async (+ Alembic para migrações). Services passam a receber repositórios por injeção de dependência.
- **Fila de verdade**: `BackgroundTasks` roda no mesmo processo — se ele cair, o evento se perde. Para volume/confiabilidade, troque por uma fila (arq/Redis, Celery ou RabbitMQ): o endpoint publica o evento e um worker separado consome.
- **Idempotência**: provedores reenviam eventos. Persista o `event_id` processado (tabela ou Redis com TTL) e ignore duplicados antes de processar.
- **Retries de saída**: para chamadas a APIs externas, use `httpx` com retry/backoff (ex.: `tenacity`).
- **Observabilidade**: os logs JSON já são estruturados; acrescente métricas (`prometheus-fastapi-instrumentator`) e tracing (OpenTelemetry) quando houver múltiplos serviços.
- **Múltiplos domínios**: agrupe por contexto (`app/routers/webhooks/bitrix/`, `app/services/bitrix/`…) mantendo o mesmo padrão de camadas.
- **CI/CD**: o `make check` é o pipeline local — replique-o no CI (GitHub Actions/GitLab CI) e faça build da imagem Docker.

## Padrões e convenções

- Tipagem obrigatória em funções (`mypy` com `disallow_untyped_defs`).
- Logs sempre via `get_logger(__name__)`, com contexto em `extra={"extra_data": {...}}` — nunca `print`.
- Erros de domínio sempre via subclasses de `AppError` — nunca `HTTPException` dentro de services.
- Segredos apenas em `.env` (nunca commitado); `.env.example` documenta as variáveis.
- Linha de até 100 colunas, imports ordenados — tudo automatizado pelo `ruff` no save/commit.
