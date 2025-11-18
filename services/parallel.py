"""Parallel processing utilities for batch operations."""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Callable, List, Any
from uuid import UUID
import multiprocessing


def process_in_parallel(
    items: List[UUID],
    process_func: Callable[[UUID], None],
    max_workers: int = None,
    use_threads: bool = False,
) -> None:
    """
    Обрабатывает список элементов параллельно.
    
    Args:
        items: список UUID для обработки
        process_func: функция обработки одного элемента
        max_workers: количество воркеров (по умолчанию = количество CPU)
        use_threads: использовать threads вместо processes (для I/O-bound задач)
    """
    if not items:
        print("No items to process")
        return
    
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    
    print(f"Processing {len(items)} items with {max_workers} workers ({'threads' if use_threads else 'processes'})...")
    
    with executor_class(max_workers=max_workers) as executor:
        # Запускаем все задачи
        future_to_item = {
            executor.submit(process_func, item): item 
            for item in items
        }
        
        # Собираем результаты
        completed = 0
        failed = 0
        
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                future.result()
                completed += 1
                if completed % 10 == 0:
                    print(f"Progress: {completed}/{len(items)} completed, {failed} failed")
            except Exception as e:
                failed += 1
                print(f"Error processing {item}: {e}")
        
        print(f"Completed: {completed} succeeded, {failed} failed")


def process_downloads_parallel(max_workers: int = 4) -> None:
    """Скачивает видео параллельно."""
    from services.downloader import download_and_store_reel_video as _download_func
    from services.supabase_client import get_supabase_client
    from uuid import UUID
    
    supabase = get_supabase_client()
    result = supabase.table("reels").select("id").is_("storage_video_path", "null").execute()
    reel_ids = [UUID(row["id"]) for row in result.data]
    
    if not reel_ids:
        print("No videos to download")
        return
    
    # Для скачивания используем threads (I/O-bound)
    process_in_parallel(
        reel_ids,
        _download_func,
        max_workers=max_workers,
        use_threads=True,  # I/O-bound задача
    )


def process_analysis_parallel(max_workers: int = 2) -> None:
    """Анализирует рилсы параллельно."""
    from services.analyzer import analyze_reel_raw
    from services.supabase_client import get_supabase_client
    from uuid import UUID
    
    supabase = get_supabase_client()
    result = supabase.table("reels").select("id").not_.is_("storage_video_path", "null").execute()
    reel_ids_with_video = {UUID(row["id"]) for row in result.data}
    
    analyzed_result = supabase.table("reel_analysis_raw").select("reel_id").execute()
    analyzed_reel_ids = {UUID(row["reel_id"]) for row in analyzed_result.data}
    
    pending_reel_ids = list(reel_ids_with_video - analyzed_reel_ids)
    
    if not pending_reel_ids:
        print("No reels to analyze")
        return
    
    # Для анализа используем processes (CPU-bound из-за Whisper/OCR)
    process_in_parallel(
        pending_reel_ids,
        analyze_reel_raw,
        max_workers=max_workers,
        use_threads=False,  # CPU-bound задача
    )


def process_hooks_parallel(max_workers: int = 4) -> None:
    """Классифицирует хуки параллельно."""
    from services.analyzer_hooks import classify_hook_with_llm
    from services.supabase_client import get_supabase_client
    from uuid import UUID
    
    supabase = get_supabase_client()
    result = supabase.table("reel_analysis_raw").select("reel_id").execute()
    reel_ids_with_raw = {UUID(row["reel_id"]) for row in result.data}
    
    hooks_result = supabase.table("hooks").select("reel_id").execute()
    reel_ids_with_hooks = {UUID(row["reel_id"]) for row in hooks_result.data}
    
    pending_reel_ids = list(reel_ids_with_raw - reel_ids_with_hooks)
    
    if not pending_reel_ids:
        print("No hooks to classify")
        return
    
    # Для LLM используем threads (I/O-bound, ожидание API)
    process_in_parallel(
        pending_reel_ids,
        classify_hook_with_llm,
        max_workers=max_workers,
        use_threads=True,  # I/O-bound задача
    )



