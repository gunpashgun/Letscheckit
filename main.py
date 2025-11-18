#!/usr/bin/env python3
"""Main CLI for Instagram reels processing pipeline."""
import argparse
import logging
import os
import sys
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

from services.ingestion import ingest_apify_json
from services.downloader import download_and_store_reel_video
from services.analyzer_raw import analyze_reel_raw
from services.analyzer_hooks_detailed import analyze_hooks_and_brands
from services.scoring import update_reel_scores
from services.supabase_client import get_supabase_client

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_ingest(args):
    """Команда: ingest --json path/to/file.json"""
    json_path = Path(args.json)
    
    if not json_path.exists():
        logger.error(f"Файл не найден: {json_path}")
        sys.exit(1)
    
    try:
        reel_ids = ingest_apify_json(str(json_path))
        logger.info(f"Успешно обработано {len(reel_ids)} рилсов")
        print(f"Reel IDs: {[str(rid) for rid in reel_ids[:5]]}...")  # Показываем первые 5
    except Exception as e:
        logger.error(f"Ошибка инжеста: {e}", exc_info=True)
        sys.exit(1)


def cmd_download_videos(args):
    """Команда: download-videos"""
    supabase = get_supabase_client()
    
    # Получаем все reels без storage_video_path
    result = supabase.table("reels").select("id").is_("storage_video_path", "null").execute()
    
    if not result.data:
        logger.info("Нет рилсов для скачивания")
        return
    
    reel_ids = [UUID(item["id"]) for item in result.data]
    logger.info(f"Найдено {len(reel_ids)} рилсов для скачивания")
    
    success_count = 0
    error_count = 0
    
    for reel_id in reel_ids:
        try:
            logger.info(f"Скачивание видео для reel {reel_id}")
            download_and_store_reel_video(reel_id)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка скачивания reel {reel_id}: {e}", exc_info=True)
            error_count += 1
    
    logger.info(f"Завершено: успешно {success_count}, ошибок {error_count}")


def cmd_analyze_raw(args):
    """Команда: analyze-raw"""
    supabase = get_supabase_client()
    
    # Получаем все reels с storage_video_path, но без записи в reel_analysis_raw
    result = supabase.table("reels").select("id").not_.is_("storage_video_path", "null").execute()
    
    if not result.data:
        logger.info("Нет рилсов для анализа")
        return
    
    all_reel_ids = [UUID(item["id"]) for item in result.data]
    
    # Проверяем, какие уже имеют анализ
    analyzed_result = supabase.table("reel_analysis_raw").select("reel_id").execute()
    analyzed_ids = {UUID(item["reel_id"]) for item in analyzed_result.data} if analyzed_result.data else set()
    
    reel_ids = [rid for rid in all_reel_ids if rid not in analyzed_ids]
    
    if not reel_ids:
        logger.info("Все рилсы уже проанализированы")
        return
    
    logger.info(f"Найдено {len(reel_ids)} рилсов для анализа")
    
    success_count = 0
    error_count = 0
    
    for reel_id in reel_ids:
        try:
            logger.info(f"Анализ рилса {reel_id}")
            analyze_reel_raw(reel_id)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка анализа reel {reel_id}: {e}", exc_info=True)
            error_count += 1
    
    logger.info(f"Завершено: успешно {success_count}, ошибок {error_count}")


def cmd_classify_hooks(args):
    """Команда: classify-hooks - детальный анализ хуков и брендов через LLM"""
    supabase = get_supabase_client()
    
    # Получаем все reels с analysis_context, но без hooks
    result = supabase.table("reel_analysis_raw").select("reel_id").not_.is_("analysis_context", "null").execute()
    
    if not result.data:
        logger.info("Нет рилсов с analysis_context")
        return
    
    all_reel_ids = [UUID(item["reel_id"]) for item in result.data]
    
    # Проверяем, какие уже имеют hooks
    hooks_result = supabase.table("hooks").select("reel_id").execute()
    hooked_ids = {UUID(item["reel_id"]) for item in hooks_result.data} if hooks_result.data else set()
    
    reel_ids = [rid for rid in all_reel_ids if rid not in hooked_ids]
    
    if not reel_ids:
        logger.info("Все рилсы уже классифицированы")
        return
    
    logger.info(f"Найдено {len(reel_ids)} рилсов для детального анализа хуков и брендов")
    
    success_count = 0
    error_count = 0
    
    for reel_id in reel_ids:
        try:
            logger.info(f"Детальный анализ хуков и брендов для reel {reel_id}")
            analyze_hooks_and_brands(reel_id)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка анализа reel {reel_id}: {e}", exc_info=True)
            error_count += 1
    
    logger.info(f"Завершено: успешно {success_count}, ошибок {error_count}")


def cmd_update_scores(args):
    """Команда: update-scores"""
    supabase = get_supabase_client()
    
    # Получаем все reels
    result = supabase.table("reels").select("id").execute()
    
    if not result.data:
        logger.info("Нет рилсов в БД")
        return
    
    reel_ids = [UUID(item["id"]) for item in result.data]
    logger.info(f"Обновление скоринга для {len(reel_ids)} рилсов")
    
    success_count = 0
    error_count = 0
    
    for reel_id in reel_ids:
        try:
            update_reel_scores(reel_id)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка обновления скора для reel {reel_id}: {e}", exc_info=True)
            error_count += 1
    
    logger.info(f"Завершено: успешно {success_count}, ошибок {error_count}")


def main():
    parser = argparse.ArgumentParser(description="Instagram Reels Processing Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Команды")
    
    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Импорт JSON от Apify")
    ingest_parser.add_argument("--json", required=True, help="Путь к JSON файлу")
    
    # download-videos
    subparsers.add_parser("download-videos", help="Скачать видео для всех рилсов без storage_video_path")
    
    # analyze-raw
    subparsers.add_parser("analyze-raw", help="Анализ текста (ASR + OCR + caption) для всех рилсов")
    
    # classify-hooks
    subparsers.add_parser("classify-hooks", help="Классификация хуков через LLM для всех рилсов")
    
    # update-scores
    subparsers.add_parser("update-scores", help="Пересчёт метрик и hook_score")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Проверяем переменные окружения
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        logger.error("SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY должны быть установлены")
        sys.exit(1)
    
    # Выполняем команду
    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "download-videos":
        cmd_download_videos(args)
    elif args.command == "analyze-raw":
        cmd_analyze_raw(args)
    elif args.command == "classify-hooks":
        cmd_classify_hooks(args)
    elif args.command == "update-scores":
        cmd_update_scores(args)


if __name__ == "__main__":
    main()

