.PHONY: install run test lint format typecheck check hooks

install:        ## Instala dependências (app + dev) via uv
	uv sync --all-extras

run:            ## Sobe o servidor local com reload
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:           ## Roda os testes com cobertura
	uv run pytest --cov=app

lint:           ## Linting (ruff)
	uv run ruff check app tests

format:         ## Formatação automática (ruff format + fix de imports)
	uv run ruff format app tests
	uv run ruff check --fix app tests

typecheck:      ## Verificação de tipos (mypy)
	uv run mypy app

check: lint typecheck test  ## Pipeline completo de qualidade

hooks:          ## Instala os hooks de pré-commit
	uv run pre-commit install
