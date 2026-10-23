# Imagem de produção — enxuta, sem dependências de desenvolvimento
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# Instala uv para usar o lock file e garantir reprodutibilidade
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Instala dependências e o projeto a partir do lock file
RUN uv sync --frozen --no-dev --no-editable

# Usuário não-root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
