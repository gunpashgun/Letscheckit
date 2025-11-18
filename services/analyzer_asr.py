"""ASR analysis using faster-whisper with timestamps."""
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Модель Whisper
WHISPER_MODEL = "medium"  # или "large-v2" для лучшего качества


def extract_audio_segment(video_path: Path, output_path: Path, start: float = 0.0, duration: float = 5.0) -> None:
    """Вырезает сегмент аудио из видео используя ffmpeg."""
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


def transcribe_audio_with_timestamps(audio_path: Path, language: str = "id") -> List[Dict[str, Any]]:
    """
    Транскрибирует аудио через faster-whisper с таймкодами.
    Возвращает список сегментов с start, end, text.
    """
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )
    
    # Собираем сегменты с таймкодами
    speech_segments = []
    for segment in segments:
        speech_segments.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        })
    
    logger.info(f"Транскрипция завершена, язык: {info.language}, сегментов: {len(speech_segments)}")
    
    return speech_segments

