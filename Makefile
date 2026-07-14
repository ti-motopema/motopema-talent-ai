.PHONY: install run test lint format typecheck check hooks

install:        ## Cria o venv e instala dependências (app + dev)
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

run:            ## Sobe o servidor local com reload
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:           ## Roda os testes com cobertura
	.venv/bin/pytest --cov=app

lint:           ## Linting (ruff)
	.venv/bin/ruff check app tests

format:         ## Formatação automática (ruff format + fix de imports)
	.venv/bin/ruff format app tests
	.venv/bin/ruff check --fix app tests

typecheck:      ## Verificação de tipos (mypy)
	.venv/bin/mypy app

check: lint typecheck test  ## Pipeline completo de qualidade

hooks:          ## Instala os hooks de pré-commit
	.venv/bin/pre-commit install
