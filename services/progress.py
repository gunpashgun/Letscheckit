"""Progress tracking utilities."""
from services.supabase_client import get_supabase_client


def check_download_progress() -> dict:
    """
    Проверяет прогресс скачивания видео.
    
    Returns:
        dict с статистикой:
        - total: всего рилсов
        - downloaded: скачано (есть storage_video_path)
        - pending: осталось скачать
        - percentage: процент выполнения
    """
    supabase = get_supabase_client()
    
    # Всего рилсов
    total_result = supabase.table("reels").select("id", count="exact").execute()
    total = total_result.count if hasattr(total_result, 'count') else len(total_result.data) if total_result.data else 0
    
    # Скачано (есть storage_video_path)
    downloaded_result = supabase.table("reels").select("id", count="exact").not_.is_("storage_video_path", "null").execute()
    downloaded = downloaded_result.count if hasattr(downloaded_result, 'count') else len(downloaded_result.data) if downloaded_result.data else 0
    
    # Осталось скачать
    pending_result = supabase.table("reels").select("id", count="exact").is_("storage_video_path", "null").execute()
    pending = pending_result.count if hasattr(pending_result, 'count') else len(pending_result.data) if pending_result.data else 0
    
    # Процент выполнения
    percentage = (downloaded / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "downloaded": downloaded,
        "pending": pending,
        "percentage": round(percentage, 2),
    }


def print_download_progress() -> None:
    """Выводит информацию о прогрессе скачивания."""
    progress = check_download_progress()
    
    print("\n" + "="*50)
    print("📊 Прогресс скачивания видео")
    print("="*50)
    print(f"Всего рилсов:        {progress['total']}")
    print(f"✅ Скачано:           {progress['downloaded']}")
    print(f"⏳ Осталось:          {progress['pending']}")
    print(f"📈 Прогресс:          {progress['percentage']}%")
    print("="*50 + "\n")
    
    # Визуальный прогресс-бар
    if progress['total'] > 0:
        bar_length = 40
        filled = int(bar_length * progress['percentage'] / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}] {progress['percentage']}%\n")


if __name__ == "__main__":
    print_download_progress()

