"""Audio analysis service using Whisper."""
import logging
from pathlib import Path
from uuid import UUID
import tempfile

from faster_whisper import WhisperModel
from supabase import Client
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Модель Whisper (можно изменить на large-v2 для лучшего качества)
WHISPER_MODEL = "medium"


def extract_audio_segment(video_path: Path, output_path: Path, start: float = 0.0, duration: float = 4.0) -> None:
    """Вырезает сегмент аудио из видео используя ffmpeg через subprocess."""
    import subprocess
    
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-ss", str(start),
        "-t", str(duration),
        "-vn",  # без видео
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "16000",  # sample rate для Whisper
        "-ac", "1",  # моно
        "-y",  # перезаписать выходной файл
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")


def transcribe_audio(audio_path: Path, language: str = "id") -> str:
    """
    Транскрибирует аудио через faster-whisper.
    Возвращает текст первых N секунд.
    """
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )
    
    # Собираем текст из сегментов
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())
    
    full_text = " ".join(text_parts)
    logger.info(f"Транскрипция завершена, язык: {info.language}, текст: {full_text[:100]}...")
    
    return full_text

