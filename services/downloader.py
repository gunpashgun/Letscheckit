"""Video downloader service."""
import logging
from pathlib import Path
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from supabase import Client
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Headers для скачивания
DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.RequestError)),
    reraise=True
)
def download_and_store_reel_video(reel_id: UUID) -> None:
    """
    По reel_id из БД берет source_video_url,
    скачивает видео и кладет в Supabase Storage.
    Обновляет reels.storage_video_path.
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select("source_video_url, shortcode, creator_id").eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не найден в БД")
    
    reel_data = result.data[0]
    video_url = reel_data["source_video_url"]
    shortcode = reel_data.get("shortcode", "")
    creator_id = reel_data.get("creator_id")
    
    if not video_url:
        raise ValueError(f"Reel {reel_id} не имеет source_video_url")
    
    # Получаем username из creators
    username = "unknown"
    if creator_id:
        creator_result = supabase.table("creators").select("username").eq("id", creator_id).execute()
        if creator_result.data:
            username = creator_result.data[0]["username"]
    
    # Формируем путь в Storage
    storage_path = f"{username}/{shortcode or str(reel_id)}.mp4"
    
    logger.info(f"Скачивание видео для reel {reel_id} из {video_url}")
    
    # Скачиваем видео стримом (следовать за редиректами)
    with httpx.Client(headers=DOWNLOAD_HEADERS, timeout=60.0, follow_redirects=True) as client:
        with client.stream("GET", video_url) as response:
            response.raise_for_status()
            
            # Создаём временный файл
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / f"{reel_id}.mp4"
            
            with open(temp_file, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    
    logger.info(f"Видео скачано, размер: {temp_file.stat().st_size} bytes")
    
    # Загружаем в Supabase Storage
    bucket_name = "reels"
    
    with open(temp_file, "rb") as f:
        file_data = f.read()
        supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "video/mp4", "upsert": "true"}
        )
    
    logger.info(f"Видео загружено в Storage: {storage_path}")
    
    # Обновляем storage_video_path в БД
    supabase.table("reels").update({"storage_video_path": storage_path}).eq("id", str(reel_id)).execute()
    
    # Удаляем временный файл
    temp_file.unlink()

