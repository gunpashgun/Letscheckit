"""Raw analysis service with timestamps: ASR, OCR, visual events."""
import logging
import json
import re
import shutil
from pathlib import Path
from uuid import UUID
import tempfile

from supabase import Client
from services.supabase_client import get_supabase_client
from services.analyzer_asr import extract_audio_segment, transcribe_audio_with_timestamps
from services.analyzer_ocr_timed import ocr_frame_at_times
from services.analyzer_visual_events import detect_visual_events

logger = logging.getLogger(__name__)


def analyze_reel_raw(reel_id: UUID) -> None:
    """
    Детальный анализ рилса с таймкодами:
    - ASR с сегментами (0-5 секунд)
    - OCR по кадрам (0.2s, 1.0s, 2.0s, 3.0s, 4.0s)
    - Визуальные события
    - Формирование JSON контекста для LLM
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select(
        "storage_video_path, caption, hashtags, url"
    ).eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не найден в БД")
    
    reel_data = result.data[0]
    storage_path = reel_data.get("storage_video_path")
    caption = reel_data.get("caption", "")
    hashtags = reel_data.get("hashtags", [])
    
    if not storage_path:
        raise ValueError(f"Reel {reel_id} не имеет storage_video_path")
    
    logger.info(f"Детальный анализ рилса {reel_id}, видео: {storage_path}")
    
    # Создаём временную директорию
    temp_dir = Path(tempfile.mkdtemp())
    video_file = temp_dir / "video.mp4"
    audio_file = temp_dir / "audio.wav"
    
    try:
        # Скачиваем видео из Storage
        bucket_name = "reels"
        video_data = supabase.storage.from_(bucket_name).download(storage_path)
        
        with open(video_file, "wb") as f:
            f.write(video_data)
        
        logger.info(f"Видео скачано из Storage: {len(video_data)} bytes")
        
        # 1. ASR: вырезаем первые 5 секунд аудио и транскрибируем с таймкодами
        logger.info("Извлечение аудио и транскрипция с таймкодами...")
        extract_audio_segment(video_file, audio_file, start=0.0, duration=5.0)
        speech_segments = transcribe_audio_with_timestamps(audio_file, language="id")
        
        logger.info(f"ASR: извлечено {len(speech_segments)} сегментов речи")
        
        # 2. OCR: извлекаем текст с экрана в конкретные моменты времени
        ocr_times = [0.2, 1.0, 2.0, 3.0, 4.0]
        logger.info(f"OCR: анализ кадров в моменты {ocr_times}...")
        onscreen_text_segments = ocr_frame_at_times(video_file, ocr_times)
        
        logger.info(f"OCR: извлечено {len(onscreen_text_segments)} текстовых сегментов")
        
        # 3. Визуальные события: анализируем те же кадры
        logger.info("Определение визуальных событий...")
        visual_events = detect_visual_events(video_file, ocr_times)
        
        logger.info(f"Визуальные события: обнаружено {len(visual_events)} событий")
        
        # 4. Извлекаем caption intro (первые 1-2 строки)
        caption_intro = _extract_caption_intro(caption)
        
        # 5. Извлекаем mentions из caption (если есть @username)
        mentions = _extract_mentions(caption)
        
        # 6. Формируем единый JSON контекст для LLM
        analysis_context = {
            "window_seconds": 5,
            "speech_segments": speech_segments,
            "onscreen_text_segments": onscreen_text_segments,
            "visual_events": visual_events,
            "caption_intro": caption_intro,
            "hashtags": hashtags,
            "mentions": mentions,
            "tagged_users": mentions,  # пока используем mentions как tagged_users
        }
        
        logger.info(f"JSON контекст сформирован: {len(speech_segments)} speech, {len(onscreen_text_segments)} text, {len(visual_events)} visual")
        
        # 7. Формируем hook_raw_text для обратной совместимости
        speech_text = " ".join([seg["text"] for seg in speech_segments])
        screen_text = " ".join([seg["text"] for seg in onscreen_text_segments])
        hook_raw_text = f"{speech_text} | {screen_text} | {caption_intro}".strip()
        
        # 8. Сохраняем в reel_analysis_raw
        analysis_data = {
            "reel_id": str(reel_id),
            "speech_text": speech_text,  # для обратной совместимости
            "screen_text": screen_text,   # для обратной совместимости
            "caption_hook_text": caption_intro,
            "hook_raw_text": hook_raw_text,
            "speech_segments": speech_segments,
            "onscreen_text_segments": onscreen_text_segments,
            "visual_events": visual_events,
            "analysis_context": analysis_context,
        }
        
        # Проверяем, есть ли уже запись
        existing = supabase.table("reel_analysis_raw").select("id").eq("reel_id", str(reel_id)).execute()
        
        if existing.data:
            supabase.table("reel_analysis_raw").update(analysis_data).eq("reel_id", str(reel_id)).execute()
            logger.info(f"Обновлена запись анализа для reel {reel_id}")
        else:
            supabase.table("reel_analysis_raw").insert(analysis_data).execute()
            logger.info(f"Создана запись анализа для reel {reel_id}")
    
    finally:
        # Очистка временных файлов
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def _extract_caption_intro(caption: str, max_lines: int = 2) -> str:
    """Извлекает первые 1-2 строки из caption."""
    if not caption:
        return ""
    
    lines = caption.split("\n")
    intro_lines = lines[:max_lines]
    return "\n".join(intro_lines).strip()


def _extract_mentions(caption: str) -> list:
    """Извлекает упоминания (@username) из caption."""
    if not caption:
        return []
    
    mentions = re.findall(r'@(\w+)', caption)
    return list(set(mentions))  # убираем дубликаты
