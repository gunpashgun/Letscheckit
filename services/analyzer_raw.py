"""Raw analysis service combining ASR, OCR, and caption extraction."""
import logging
import re
import shutil
from pathlib import Path
from uuid import UUID
import tempfile

from supabase import Client
from services.supabase_client import get_supabase_client
from services.analyzer_audio import extract_audio_segment, transcribe_audio
from services.analyzer_ocr import extract_frames, ocr_frames

logger = logging.getLogger(__name__)


def analyze_reel_raw(reel_id: UUID) -> None:
    """
    Для данного reel:
    - скачивает видео из Supabase,
    - извлекает первые секунды аудио/видео,
    - получает speech_text (Whisper),
    - получает screen_text (OCR),
    - формирует caption_hook_text,
    - сохраняет в reel_analysis_raw.
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select("storage_video_path, caption").eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не найден в БД")
    
    reel_data = result.data[0]
    storage_path = reel_data.get("storage_video_path")
    caption = reel_data.get("caption", "")
    
    if not storage_path:
        raise ValueError(f"Reel {reel_id} не имеет storage_video_path")
    
    logger.info(f"Анализ рилса {reel_id}, видео: {storage_path}")
    
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
        
        # 1. ASR: вырезаем первые 4 секунды аудио и транскрибируем
        logger.info("Извлечение аудио и транскрипция...")
        extract_audio_segment(video_file, audio_file, start=0.0, duration=4.0)
        speech_text = transcribe_audio(audio_file, language="id")
        
        # 2. OCR: извлекаем кадры и делаем OCR
        logger.info("Извлечение кадров и OCR...")
        frames = extract_frames(video_file, num_frames=3, start_time=0.0, duration=3.0)
        screen_text = ocr_frames(frames)
        
        # 3. Caption hook: берём первые 1-2 предложения из caption
        caption_hook_text = _extract_caption_hook(caption)
        
        # 4. Формируем hook_raw_text
        hook_raw_text = f"{speech_text} | {screen_text} | {caption_hook_text}".strip()
        
        logger.info(f"hook_raw_text сформирован, длина: {len(hook_raw_text)}")
        
        # 5. Сохраняем в reel_analysis_raw
        analysis_data = {
            "reel_id": str(reel_id),
            "speech_text": speech_text,
            "screen_text": screen_text,
            "caption_hook_text": caption_hook_text,
            "hook_raw_text": hook_raw_text,
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


def _extract_caption_hook(caption: str, max_length: int = 200) -> str:
    """
    Извлекает хук из caption: первые 1-2 предложения, обрезает до max_length символов.
    """
    if not caption:
        return ""
    
    # Разбиваем на предложения (по точкам, восклицательным, вопросительным знакам)
    sentences = re.split(r'[.!?]+', caption)
    
    # Берём первые 1-2 предложения
    hook_sentences = []
    total_length = 0
    
    for sent in sentences[:2]:
        sent = sent.strip()
        if not sent:
            continue
        
        if total_length + len(sent) + 1 <= max_length:
            hook_sentences.append(sent)
            total_length += len(sent) + 1
        else:
            # Обрезаем последнее предложение
            remaining = max_length - total_length - 1
            if remaining > 20:  # Минимум символов для добавления
                hook_sentences.append(sent[:remaining] + "...")
            break
    
    result = ". ".join(hook_sentences)
    
    # Если всё ещё слишком длинное, обрезаем
    if len(result) > max_length:
        result = result[:max_length - 3] + "..."
    
    return result

