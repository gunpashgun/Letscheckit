"""Video downloader service."""
from uuid import UUID
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from services.supabase_client import get_supabase_client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_and_store_reel_video(reel_id: UUID) -> None:
    """
    По reel_id из БД берет source_video_url,
    скачивает видео и кладет в Supabase Storage.
    Обновляет reels.storage_video_path.
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select("*").eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} not found")
    
    reel = result.data[0]
    
    if not reel.get("source_video_url"):
        raise ValueError(f"Reel {reel_id} has no source_video_url")
    
    if reel.get("storage_video_path"):
        print(f"Reel {reel_id} already has storage_video_path, skipping")
        return
    
    # Получаем username для пути
    creator_result = supabase.table("creators").select("username").eq("id", reel["creator_id"]).execute()
    username = creator_result.data[0]["username"] if creator_result.data else "unknown"
    
    video_url = reel["source_video_url"]
    shortcode = reel.get("shortcode") or reel["ig_reel_id"]
    
    # Формируем путь в Storage
    storage_path = f"{username}/{shortcode}.mp4"
    
    # Скачиваем видео
    with httpx.Client(timeout=60.0) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = client.get(video_url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        
        # Загружаем в Supabase Storage
        bucket = "reels"
        
        # Проверяем существование bucket или создаём (если есть права)
        try:
            supabase.storage.from_(bucket).upload(
                storage_path,
                response.content,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
        except Exception as e:
            # Если bucket не существует, создаём его (требует прав)
            print(f"Upload error: {e}")
            raise
    
    # Обновляем storage_video_path в БД
    supabase.table("reels").update({"storage_video_path": storage_path}).eq("id", str(reel_id)).execute()
    
    print(f"Downloaded and stored video for reel {reel_id} at {storage_path}")


def download_all_pending_videos() -> None:
    """Скачивает все видео, у которых нет storage_video_path."""
    supabase = get_supabase_client()
    
    result = supabase.table("reels").select("id").is_("storage_video_path", "null").execute()
    
    reel_ids = [UUID(row["id"]) for row in result.data]
    
    total = len(reel_ids)
    print(f"Found {total} reels without videos")
    
    if total == 0:
        return
    
    success_count = 0
    error_count = 0
    
    for idx, reel_id in enumerate(reel_ids, 1):
        try:
            print(f"[{idx}/{total}] Processing reel {reel_id}...")
            download_and_store_reel_video(reel_id)
            success_count += 1
            
            # Показываем прогресс каждые 10 видео
            if idx % 10 == 0:
                print(f"Progress: {idx}/{total} ({success_count} success, {error_count} errors)")
        except Exception as e:
            error_count += 1
            print(f"Error processing reel {reel_id}: {e}")
            continue
    
    print(f"\n✅ Completed: {success_count} succeeded, {error_count} failed out of {total} total")

