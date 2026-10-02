"""Recurso: avaliações de candidatos.

POST /api/v1/evaluations/video   — analisa vídeo da prova prática de venda
POST /api/v1/evaluations/resume  — analisa currículo (PDF ou TXT)
"""

import asyncio
import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import PayloadValidationError
from app.logging_config import get_logger
from app.services.openai_service import OpenAIService

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluations", tags=["Avaliações"])

_MAX_VIDEO_BYTES = 500 * 1024 * 1024
_MAX_DOC_BYTES = 10 * 1024 * 1024
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CandidatoFormulario(BaseModel):
    """Formulário de triagem do candidato — todos os campos opcionais."""

    telefone: str | None = None
    cidade: str | None = None
    bairro: str | None = None
    estado_civil: str | None = None
    filhos: str | None = None
    possui_cnh: str | None = None
    possui_veiculo_proprio: str | None = None
    link_rede_social: str | None = None
    formacao_academica: str | None = None
    status_graduacao: str | None = None
    curso_superior: str | None = None
    possui_cursos_extras: str | None = None
    quais_cursos_extras: str | None = None
    participacao_renda_familiar: str | None = None
    motivacao_vendas: str | None = None
    atuacao_ambiente_vendas: str | None = None
    abordagens_externas: str | None = None
    pretensao_salarial: str | None = None


class PerfilComportamental(BaseModel):
    """32 respostas do questionário comportamental — todos os campos opcionais."""

    resposta_01: str | None = None
    resposta_02: str | None = None
    resposta_03: str | None = None
    resposta_04: str | None = None
    resposta_05: str | None = None
    resposta_06: str | None = None
    resposta_07: str | None = None
    resposta_08: str | None = None
    resposta_09: str | None = None
    resposta_10: str | None = None
    resposta_11: str | None = None
    resposta_12: str | None = None
    resposta_13: str | None = None
    resposta_14: str | None = None
    resposta_15: str | None = None
    resposta_16: str | None = None
    resposta_17: str | None = None
    resposta_18: str | None = None
    resposta_19: str | None = None
    resposta_20: str | None = None
    resposta_21: str | None = None
    resposta_22: str | None = None
    resposta_23: str | None = None
    resposta_24: str | None = None
    resposta_25: str | None = None
    resposta_26: str | None = None
    resposta_27: str | None = None
    resposta_28: str | None = None
    resposta_29: str | None = None
    resposta_30: str | None = None
    resposta_31: str | None = None
    resposta_32: str | None = None


class BehavioralProfileResponse(BaseModel):
    nome_completo: str
    evaluation: dict[str, Any] | str


class SummarizeRequest(BaseModel):
    nome_completo: str
    resultado_perfil: str | None = None
    resultado_video: str | None = None
    resultado_curriculo: str | None = None


class SummarizeResponse(BaseModel):
    nome_completo: str
    fontes_utilizadas: list[str]
    resumo: dict[str, Any] | str


class VideoEvaluationResponse(BaseModel):
    filename: str | None = None
    mime_type: str
    size_bytes: int
    evaluation: dict[str, Any] | str


class ResumeEvaluationResponse(BaseModel):
    nome_completo: str
    formulario: CandidatoFormulario | None = None
    filename: str | None = None
    pages: int
    evaluation: dict[str, Any] | str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_prompt(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("prompt file not found", extra={"extra_data": {"path": path}})
        return ""


def _detect_mime(file: UploadFile) -> str:
    if file.content_type and file.content_type.startswith("video/"):
        return file.content_type
    if file.filename:
        guessed, _ = mimetypes.guess_type(file.filename)
        if guessed and guessed.startswith("video/"):
            return guessed
    return "video/mp4"


def _pdf_to_images(content: bytes, max_pages: int = 10) -> tuple[list[str], int]:
    """Renderiza páginas do PDF como JPEG base64. Funciona com PDFs de texto e escaneados."""
    import fitz  # pymupdf — lazy import

    doc = fitz.open(stream=content, filetype="pdf")
    total = len(doc)
    matrix = fitz.Matrix(1.5, 1.5)  # 1.5x scale — adequate quality without excessive size

    images = [
        base64.b64encode(doc[i].get_pixmap(matrix=matrix).tobytes("jpeg")).decode()
        for i in range(min(total, max_pages))
    ]

    doc.close()
    return images, total


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_video_service(settings=Depends(get_settings)) -> OpenAIService:
    return OpenAIService(
        api_key=settings.llm_api_key,
        model_name=settings.llm_model,
        system_prompt=_load_prompt(settings.prompt_video_path),
        use_json_format=True,
        transcription_model=settings.llm_transcription_model,
    )


def get_resume_service(settings=Depends(get_settings)) -> OpenAIService:
    return OpenAIService(
        api_key=settings.llm_api_key,
        model_name=settings.llm_model,
        system_prompt=_load_prompt(settings.prompt_curriculo_path),
        use_json_format=True,
    )


def get_behavioral_service(settings=Depends(get_settings)) -> OpenAIService:
    return OpenAIService(
        api_key=settings.llm_api_key,
        model_name=settings.llm_model,
        system_prompt=_load_prompt(settings.prompt_comportamental_path),
        use_json_format=True,
    )


def get_consolidated_service(settings=Depends(get_settings)) -> OpenAIService:
    return OpenAIService(
        api_key=settings.llm_api_key,
        model_name=settings.llm_model,
        system_prompt=_load_prompt(settings.prompt_consolidado_path),
        use_json_format=True,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/video", status_code=201, response_model=VideoEvaluationResponse)
async def create_video_evaluation(
    file: UploadFile = File(..., description="Vídeo da prova prática (MP4, MOV, WEBM…)"),
    prompt: str | None = Form(default=None, description="Instrução adicional ao modelo (opcional)"),
    service: OpenAIService = Depends(get_video_service),
) -> VideoEvaluationResponse:
    """Analisa o vídeo da prova prática de venda e retorna relatório estruturado."""
    content = await file.read()

    if not content:
        raise PayloadValidationError("Arquivo de vídeo vazio.")
    if len(content) > _MAX_VIDEO_BYTES:
        raise PayloadValidationError(
            f"Arquivo muito grande ({len(content) // (1024 * 1024)} MB). Limite: 500 MB."
        )

    mime_type = _detect_mime(file)
    effective_prompt = prompt or ""

    logger.info(
        "video evaluation started",
        extra={"extra_data": {"filename": file.filename, "mime": mime_type,
                              "size_mb": round(len(content) / (1024 * 1024), 2)}},
    )

    raw = await asyncio.to_thread(service.analyze_video, content, mime_type, effective_prompt)

    logger.info("ai response received", extra={"extra_data": {"raw": raw}})

    evaluation: dict[str, Any] | str
    try:
        evaluation = json.loads(raw)
    except json.JSONDecodeError:
        evaluation = raw

    logger.info("ai evaluation parsed", extra={"extra_data": {"evaluation": evaluation}})

    return VideoEvaluationResponse(
        filename=file.filename,
        mime_type=mime_type,
        size_bytes=len(content),
        evaluation=evaluation,
    )


@router.post("/resume", status_code=201, response_model=ResumeEvaluationResponse)
async def create_resume_evaluation(
    nome_completo: str = Form(..., description="Nome completo do candidato"),
    formulario: str | None = Form(default=None, description="Formulário serializado em JSON"),
    file: UploadFile | None = File(default=None, description="Currículo (PDF, DOCX ou TXT)"),
    prompt: str | None = Form(default=None, description="Instrução adicional ao modelo (opcional)"),
    service: OpenAIService = Depends(get_resume_service),
) -> ResumeEvaluationResponse:
    """Analisa o currículo do candidato e retorna relatório estruturado."""
    parsed_formulario: CandidatoFormulario | None = None
    if formulario:
        try:
            parsed_formulario = CandidatoFormulario.model_validate_json(formulario)
        except Exception as exc:
            raise PayloadValidationError(
                "Formulário inválido. Envie um JSON válido no campo 'formulario'."
            ) from exc

    if not file:
        raise PayloadValidationError("Envie o currículo (PDF, imagem, DOCX ou TXT).")

    content = await file.read()
    if not content:
        raise PayloadValidationError("Arquivo de currículo vazio.")
    if len(content) > _MAX_DOC_BYTES:
        raise PayloadValidationError(
            f"Arquivo muito grande ({len(content) // (1024 * 1024)} MB). Limite: 10 MB."
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".docx"} | _IMAGE_SUFFIXES:
        raise PayloadValidationError(
            "Formato não suportado. Envie PDF, DOCX, imagem (JPG/PNG/WEBP) ou TXT."
        )

    effective_prompt = prompt or ""
    if parsed_formulario:
        form_context = "Formulário preenchido pelo candidato:\n" + json.dumps(
            parsed_formulario.model_dump(exclude_none=True), ensure_ascii=False, indent=2
        )
        effective_prompt = f"{form_context}\n\n{effective_prompt}".strip()

    pages = 0

    if suffix == ".pdf":
        page_images, pages = _pdf_to_images(content)
        if not page_images:
            raise PayloadValidationError("Não foi possível renderizar o PDF.")
        logger.info(
            "resume evaluation started (PDF)",
            extra={"extra_data": {"filename": file.filename, "pages": pages}},
        )
        raw = await asyncio.to_thread(
            service.analyze_pdf_images, page_images, effective_prompt, None
        )

    elif suffix in _IMAGE_SUFFIXES:
        image_b64 = base64.b64encode(content).decode()
        pages = 1
        logger.info(
            "resume evaluation started (image)",
            extra={"extra_data": {"filename": file.filename}},
        )
        raw = await asyncio.to_thread(
            service.analyze_pdf_images, [image_b64], effective_prompt, None
        )

    elif suffix == ".docx":
        from io import BytesIO

        import docx
        doc = docx.Document(BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if not text.strip():
            raise PayloadValidationError("Não foi possível extrair texto do DOCX.")
        pages = 1
        logger.info(
            "resume evaluation started (DOCX)",
            extra={"extra_data": {"filename": file.filename, "chars": len(text)}},
        )
        raw = await asyncio.to_thread(service.analyze_document, text, effective_prompt)

    else:
        text = content.decode("utf-8", errors="replace")
        if not text.strip():
            raise PayloadValidationError("Arquivo de texto vazio.")
        pages = 1
        logger.info(
            "resume evaluation started (TXT)",
            extra={"extra_data": {"filename": file.filename, "chars": len(text)}},
        )
        raw = await asyncio.to_thread(service.analyze_document, text, effective_prompt)

    logger.info("ai response received", extra={"extra_data": {"raw": raw}})

    evaluation: dict[str, Any] | str
    try:
        evaluation = json.loads(raw)
    except json.JSONDecodeError:
        evaluation = raw

    logger.info("ai evaluation parsed", extra={"extra_data": {"evaluation": evaluation}})

    return ResumeEvaluationResponse(
        nome_completo=nome_completo,
        formulario=parsed_formulario,
        filename=file.filename,
        pages=pages,
        evaluation=evaluation,
    )


@router.post("/behavioral-profile", status_code=201, response_model=BehavioralProfileResponse)
async def create_behavioral_profile(
    nome_completo: str = Form(..., description="Nome completo do candidato"),
    perguntas: str = Form(..., description="Respostas do questionário comportamental em JSON"),
    service: OpenAIService = Depends(get_behavioral_service),
) -> BehavioralProfileResponse:
    """Mapeia o perfil comportamental do candidato com base nas 30 respostas do questionário."""
    try:
        parsed = PerfilComportamental.model_validate_json(perguntas)
    except Exception as exc:
        raise PayloadValidationError("Campo 'perguntas' inválido. Envie um JSON válido.") from exc

    respostas_texto = json.dumps(
        parsed.model_dump(exclude_none=True), ensure_ascii=False, indent=2
    )
    prompt = f"Respostas do candidato {nome_completo}:\n\n{respostas_texto}"

    raw = await asyncio.to_thread(service.analyze_document, prompt, "")

    logger.info("ai response received", extra={"extra_data": {"raw": raw}})

    evaluation: dict[str, Any] | str
    try:
        evaluation = json.loads(raw)
    except json.JSONDecodeError:
        evaluation = raw

    logger.info("ai evaluation parsed", extra={"extra_data": {"evaluation": evaluation}})

    return BehavioralProfileResponse(
        nome_completo=nome_completo,
        evaluation=evaluation,
    )


@router.post("/summarize", status_code=201, response_model=SummarizeResponse)
async def summarize_from_crm_fields(
    body: SummarizeRequest,
    service: OpenAIService = Depends(get_consolidated_service),
) -> SummarizeResponse:
    """Gera resumo consolidado a partir dos resultados já computados no CRM.

    Recebe os campos UF_CRM_9_1790363516350 (perfil), UF_CRM_9_1790360637060
    (vídeo) e UF_CRM_9_1790164903126 (currículo) e produz o conteúdo para
    UF_CRM_9_1790942767 (resumo final).
    """
    fontes: list[str] = []
    payload: dict[str, Any] = {"candidato": body.nome_completo}

    def _parse(raw: str | None, key: str) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return raw

    if body.resultado_perfil:
        payload["perfil_comportamental"] = _parse(body.resultado_perfil, "perfil")
        fontes.append("comportamental")

    if body.resultado_video:
        payload["avaliacao_video"] = _parse(body.resultado_video, "video")
        fontes.append("video")

    if body.resultado_curriculo:
        payload["avaliacao_curriculo"] = _parse(body.resultado_curriculo, "curriculo")
        fontes.append("curriculo")

    if not fontes:
        raise PayloadValidationError(
            "Envie ao menos um resultado: resultado_perfil, resultado_video ou resultado_curriculo."
        )

    logger.info(
        "summarize started",
        extra={"extra_data": {"candidato": body.nome_completo, "fontes": fontes}},
    )

    synthesis_input = json.dumps(payload, ensure_ascii=False, indent=2)
    raw = await asyncio.to_thread(service.analyze_document, synthesis_input, "")

    logger.info("summarize response received", extra={"extra_data": {"raw": raw}})

    resumo: dict[str, Any] | str
    try:
        resumo = json.loads(raw)
    except json.JSONDecodeError:
        resumo = raw

    return SummarizeResponse(
        nome_completo=body.nome_completo,
        fontes_utilizadas=fontes,
        resumo=resumo,
    )
