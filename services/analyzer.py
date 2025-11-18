"""Main analyzer service combining audio, OCR, and caption analysis."""
import tempfile
import os
from uuid import UUID

from services.supabase_client import get_supabase_client
from services.analyzer_audio import extract_audio_text
from services.analyzer_ocr import extract_frames_ocr


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
    
    # Проверяем, есть ли уже анализ
    existing = supabase.table("reel_analysis_raw").select("id").eq("reel_id", str(reel_id)).execute()
    if existing.data:
        print(f"Reel {reel_id} already has raw analysis, skipping")
        return
    
    # Получаем данные рилса
    result = supabase.table("reels").select("*").eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} not found")
    
    reel = result.data[0]
    
    if not reel.get("storage_video_path"):
        raise ValueError(f"Reel {reel_id} has no storage_video_path")
    
    storage_path = reel["storage_video_path"]
    caption = reel.get("caption") or ""
    
    # Создаём временную директорию
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_video_path = os.path.join(temp_dir, "video.mp4")
        
        # Скачиваем видео из Supabase Storage
        bucket = "reels"
        video_data = supabase.storage.from_(bucket).download(storage_path)
        
        with open(temp_video_path, "wb") as f:
            f.write(video_data)
        
        # ASR: извлекаем текст из первых 4 секунд
        try:
            speech_text = extract_audio_text(temp_video_path, duration_seconds=4, language="id")
        except Exception as e:
            print(f"ASR error for reel {reel_id}: {e}")
            speech_text = ""
        
        # OCR: извлекаем текст с кадров (первые 2-3 секунды, 3 кадра)
        try:
            screen_text = extract_frames_ocr(temp_video_path, num_frames=3, start_time=0.0, end_time=3.0)
        except Exception as e:
            print(f"OCR error for reel {reel_id}: {e}")
            screen_text = ""
        
        # Caption hook: первые 1-2 предложения, обрезаем до 160-200 символов
        caption_hook_text = _extract_caption_hook(caption)
        
        # Формируем hook_raw_text
        hook_raw_text = f"{speech_text} | {screen_text} | {caption_hook_text}".strip()
        
        # Сохраняем в reel_analysis_raw
        analysis_data = {
            "reel_id": str(reel_id),
            "speech_text": speech_text,
            "screen_text": screen_text,
            "caption_hook_text": caption_hook_text,
            "hook_raw_text": hook_raw_text,
        }
        
        supabase.table("reel_analysis_raw").insert(analysis_data).execute()
        
        print(f"Analyzed reel {reel_id}: speech={len(speech_text)} chars, screen={len(screen_text)} chars")


def _extract_caption_hook(caption: str, max_length: int = 200) -> str:
    """Извлекает хук из caption: первые 1-2 предложения, до max_length символов."""
    if not caption:
        return ""
    
    # Разбиваем на предложения
    sentences = caption.split(". ")
    
    if len(sentences) == 1:
        # Если нет точек, берём первые слова
        words = caption.split()
        hook = " ".join(words[:20])  # примерно 1-2 предложения
    else:
        # Берём первые 1-2 предложения
        hook = ". ".join(sentences[:2])
        if not hook.endswith("."):
            hook += "."
    
    # Обрезаем до max_length
    if len(hook) > max_length:
        hook = hook[:max_length].rsplit(" ", 1)[0] + "..."
    
    return hook.strip()


def analyze_all_pending_reels() -> None:
    """Анализирует все рилсы без записи в reel_analysis_raw."""
    supabase = get_supabase_client()
    
    # Находим рилсы с видео, но без анализа
    result = supabase.table("reels").select("id").not_.is_("storage_video_path", "null").execute()
    
    reel_ids_with_video = {UUID(row["id"]) for row in result.data}
    
    analyzed_result = supabase.table("reel_analysis_raw").select("reel_id").execute()
    analyzed_reel_ids = {UUID(row["reel_id"]) for row in analyzed_result.data}
    
    pending_reel_ids = reel_ids_with_video - analyzed_reel_ids
    
    print(f"Found {len(pending_reel_ids)} reels pending raw analysis")
    
    for reel_id in pending_reel_ids:
        try:
            analyze_reel_raw(reel_id)
        except Exception as e:
            print(f"Error analyzing reel {reel_id}: {e}")
            continue

