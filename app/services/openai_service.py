"""Cliente para a API da OpenAI — análise de vídeo e documentos.

Métodos públicos:
  analyze_video      — extrai frames (ffmpeg/cv2) + transcreve áudio + analisa com GPT Vision
  analyze_pdf_images — renderiza páginas de PDF e analisa com GPT-4o Vision
  analyze_document   — envia texto puro (TXT)
"""

import base64
import glob
import os
import subprocess
import tempfile
from typing import Any

import cv2
from openai import OpenAI

from app.exceptions import ExternalServiceError
from app.logging_config import get_logger

logger = get_logger(__name__)

_MAX_FRAMES = 12
_JPEG_QUALITY = 85


class OpenAIService:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        system_prompt: str = "",
        use_json_format: bool = False,
        transcription_model: str = "gpt-4o-transcribe",
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model_name
        self._system_prompt = system_prompt
        self._use_json_format = use_json_format
        self._transcription_model = transcription_model

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    def analyze_video(self, video_bytes: bytes, mime_type: str, prompt: str) -> str:
        ext = _mime_to_ext(mime_type)

        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = os.path.join(tmp_dir, f"video{ext}")
            with open(video_path, "wb") as f:
                f.write(video_bytes)

            frames = _extract_frames_ffmpeg(video_path, tmp_dir) or _extract_frames_cv2(video_path)
            logger.info("frames extracted", extra={"extra_data": {"count": len(frames)}})

            transcript = self._transcribe(video_path, tmp_dir)
            if transcript:
                logger.info("audio transcribed", extra={"extra_data": {"chars": len(transcript)}})

            return self._call(_build_video_content(frames, transcript, prompt))

    # ------------------------------------------------------------------
    # PDF — pages as images (GPT-4o Vision)
    # ------------------------------------------------------------------

    def analyze_pdf_images(
        self,
        page_images: list[str],
        prompt: str,
        form_images: list[str] | None = None,
    ) -> str:
        """Analisa currículo (PDF) e formulário complementar como imagens JPEG base64."""
        if not page_images and not form_images:
            raise ExternalServiceError("Nenhuma página pôde ser renderizada do PDF.")

        content: list[dict[str, Any]] = [
            {"type": "text", "text": "Currículo do candidato:"},
            *[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}", "detail": "high"},
                }
                for img in page_images
            ],
        ]

        if form_images:
            content.append({"type": "text", "text": "Formulário complementar do candidato:"})
            content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}", "detail": "high"},
                }
                for img in form_images
            )

        if prompt:
            content.append({"type": "text", "text": prompt})

        logger.info(
            "analysing PDF via vision",
            extra={
                "extra_data": {
                    "cv_pages": len(page_images),
                    "form_pages": len(form_images or []),
                }
            },
        )
        return self._call(content)

    # ------------------------------------------------------------------
    # Plain text document (TXT)
    # ------------------------------------------------------------------

    def analyze_document(self, text: str, prompt: str) -> str:
        if not text.strip():
            raise ExternalServiceError("Documento sem conteúdo legível.")
        logger.info("analysing text document", extra={"extra_data": {"chars": len(text)}})
        return self._call([{"type": "text", "text": f"{prompt}\n\n---\n\n{text}"}])

    # ------------------------------------------------------------------
    # Audio transcription
    # ------------------------------------------------------------------

    def _transcribe(self, video_path: str, tmp_dir: str) -> str:
        audio_path = os.path.join(tmp_dir, "audio.mp3")
        if not _extract_audio_ffmpeg(video_path, audio_path):
            return ""
        try:
            with open(audio_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=self._transcription_model,
                    file=audio_file,
                )
            return response.text or ""
        except Exception as exc:
            logger.warning("audio transcription failed", extra={"extra_data": {"error": str(exc)}})
            return ""

    # ------------------------------------------------------------------
    # Shared call
    # ------------------------------------------------------------------

    def _call(self, user_content: list[dict[str, Any]]) -> str:
        messages: list[dict[str, Any]] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": user_content})

        kwargs: dict[str, Any] = {"model": self._model, "messages": messages}
        if self._use_json_format:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ExternalServiceError(f"OpenAI falhou: {exc}") from exc

        raw = (response.choices[0].message.content or "").strip()
        if not raw:
            raise ExternalServiceError("OpenAI retornou resposta vazia.")

        logger.info(
            "response received",
            extra={"extra_data": {"chars": len(raw), "model": self._model}},
        )
        return raw


# ------------------------------------------------------------------
# Video helpers
# ------------------------------------------------------------------


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _extract_frames_ffmpeg(video_path: str, output_dir: str) -> list[str]:
    """Extract frames at 1fps using bundled ffmpeg, capped at MAX_FRAMES."""
    pattern = os.path.join(output_dir, "frame_%04d.jpg")
    try:
        subprocess.run(
            [
                _ffmpeg_exe(), "-i", video_path,
                "-vf", "fps=1",
                "-frames:v", str(_MAX_FRAMES),
                "-q:v", "2",
                pattern, "-y",
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    frames = []
    for path in sorted(glob.glob(os.path.join(output_dir, "frame_*.jpg"))):
        with open(path, "rb") as f:
            frames.append(base64.b64encode(f.read()).decode())
    return frames


def _extract_audio_ffmpeg(video_path: str, output_path: str) -> bool:
    """Extract audio track to mp3 using bundled ffmpeg. Returns True on success."""
    try:
        cmd = [
            _ffmpeg_exe(), "-i", video_path,
            "-vn", "-acodec", "mp3", "-q:a", "4",
            output_path, "-y",
        ]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _extract_frames_cv2(video_path: str) -> list[str]:
    """Fallback frame extraction using cv2 when ffmpeg is unavailable."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // _MAX_FRAMES)
    frames: list[str] = []

    for idx in range(0, total, step):
        if len(frames) >= _MAX_FRAMES:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
        frames.append(base64.b64encode(buf).decode())

    cap.release()
    return frames


def _build_video_content(
    frames: list[str], transcript: str, prompt: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []

    if transcript:
        content.append({"type": "text", "text": f"Transcrição do áudio:\n\n{transcript}"})

    content.extend(
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{f}", "detail": "auto"},
        }
        for f in frames
    )

    if prompt:
        content.append({"type": "text", "text": prompt})

    return content


def _mime_to_ext(mime_type: str) -> str:
    return {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "video/avi": ".avi",
        "video/x-msvideo": ".avi",
        "video/x-matroska": ".mkv",
    }.get(mime_type, ".mp4")
