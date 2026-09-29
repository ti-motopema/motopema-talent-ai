# motopema-talent-ai

Plataforma de triagem de candidatos com IA para o **Grupo Motopema**. Analisa vídeos de prova prática de vendas, currículos e questionários comportamentais usando GPT-4o Vision e Whisper.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/evaluations/video` | Analisa vídeo da prova prática de venda |
| `POST` | `/api/v1/evaluations/resume` | Analisa currículo (PDF, DOCX, imagem ou TXT) |
| `POST` | `/api/v1/evaluations/behavioral` | Pontua questionário comportamental (32 respostas) |
| `GET`  | `/health` | Liveness check |
| `GET`  | `/ready` | Readiness check |

Todos os endpoints de avaliação aceitam `multipart/form-data` com campos opcionais do formulário de triagem do candidato.

## Arquitetura

```
Requisição HTTP
      │
      ▼
Middleware (request_id + log de acesso JSON)
      │
      ▼
Router (app/routers/avaliacoes.py)   ← validação, montagem do prompt
      │
      ▼
OpenAIService (app/services/)        ← extração de frames, transcrição, análise
      │
      ▼
API OpenAI (GPT-4o Vision + Whisper)
```

## Configuração

Copie `.env.example` para `.env` e preencha as variáveis:

```bash
cp .env.example .env
```

| Variável | Descrição |
|----------|-----------|
| `LLM_API_KEY` | Chave da API OpenAI |
| `LLM_MODEL` | Modelo de análise (padrão: `gpt-4o`) |
| `LLM_TRANSCRIPTION_MODEL` | Modelo de transcrição (padrão: `gpt-4o-transcribe`) |
| `PROMPT_VIDEO_PATH` | Caminho do prompt de vídeo |
| `PROMPT_CURRICULO_PATH` | Caminho do prompt de currículo |
| `PROMPT_COMPORTAMENTAL_PATH` | Caminho do prompt comportamental |

## Desenvolvimento

```bash
# Instalar dependências
make install

# Subir servidor local com reload
make run

# Rodar testes
make test

# Lint + tipos + testes
make check
```

## Prompts

Os prompts de avaliação ficam em `app/prompts/` e são carregados via variável de ambiente, podendo ser substituídos sem alterar o código.
