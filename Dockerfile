# Imagem de produção — enxuta, sem dependências de desenvolvimento
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY pyproject.toml README.md ./
COPY app ./app
RUN rm -rf *.egg-info && pip install --no-cache-dir .

# Usuário não-root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
