"""Audio analysis service using Whisper."""
import tempfile
import os
from uuid import UUID
from pathlib import Path
from faster_whisper import WhisperModel
from supabase import Client

from services.supabase_client import get_supabase_client


def extract_audio_text(video_path: str, duration_seconds: int = 4, language: str = "id") -> str:
    """
    Извлекает текст из первых N секунд аудио видео через Whisper.
    
    Args:
        video_path: путь к видеофайлу
        duration_seconds: сколько секунд обрабатывать
        language: приоритетный язык (id для индонезийского)
    
    Returns:
        Транскрибированный текст
    """
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    
    # Извлекаем первые N секунд
    segments, info = model.transcribe(
        video_path,
        language=language,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
    )
    
    # Собираем текст из сегментов, ограничивая по времени
    text_parts = []
    current_time = 0.0
    
    for segment in segments:
        if current_time >= duration_seconds:
            break
        if segment.text.strip():
            text_parts.append(segment.text.strip())
        current_time = segment.end
    
    result = " ".join(text_parts).strip()
    return result if result else ""

