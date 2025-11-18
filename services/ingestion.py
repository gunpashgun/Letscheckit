"""Ingestion service for Apify JSON data."""
import json
import logging
from typing import List
from uuid import UUID
from datetime import datetime

from supabase import Client
from models.apify_reel import ApifyReel
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def ingest_apify_json(path: str) -> List[UUID]:
    """
    Читает JSON-файл с массивом рилсов от Apify.
    Создаёт/обновляет записи в creators и reels.
    Возвращает список reel_id (UUID) в нашей БД.
    """
    supabase = get_supabase_client()
    reel_ids = []
    
    # Читаем JSON
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("JSON должен содержать массив объектов")
    
    logger.info(f"Обработка {len(data)} рилсов из {path}")
    
    for item in data:
        try:
            reel = ApifyReel(**item)
            reel_id = _process_reel(supabase, reel)
            reel_ids.append(reel_id)
        except Exception as e:
            logger.error(f"Ошибка обработки рилса {item.get('id', 'unknown')}: {e}")
            continue
    
    logger.info(f"Успешно обработано {len(reel_ids)} рилсов")
    return reel_ids


def _process_reel(supabase: Client, reel: ApifyReel) -> UUID:
    """Обрабатывает один рилс: создаёт/находит creator и создаёт/обновляет reel."""
    # 1. Создать/найти creator
    creator_id = _get_or_create_creator(supabase, reel)
    
    # 2. Создать/обновить reel
    reel_id = _get_or_create_reel(supabase, reel, creator_id)
    
    return reel_id


def _get_or_create_creator(supabase: Client, reel: ApifyReel) -> UUID:
    """Находит или создаёт creator по ownerId."""
    # Проверяем существование
    result = supabase.table("creators").select("id").eq("ig_owner_id", reel.ownerId).execute()
    
    if result.data:
        return UUID(result.data[0]["id"])
    
    # Создаём нового
    creator_data = {
        "ig_owner_id": reel.ownerId,
        "username": reel.ownerUsername,
        "full_name": reel.ownerFullName,
    }
    
    result = supabase.table("creators").insert(creator_data).execute()
    return UUID(result.data[0]["id"])


def _get_or_create_reel(supabase: Client, reel: ApifyReel, creator_id: UUID) -> UUID:
    """Находит или создаёт/обновляет reel."""
    # Проверяем существование
    result = supabase.table("reels").select("id").eq("ig_reel_id", reel.id).execute()
    
    reel_data = {
        "ig_reel_id": reel.id,
        "shortcode": reel.shortCode,
        "creator_id": str(creator_id),
        "caption": reel.caption,
        "hashtags": reel.hashtags,
        "url": str(reel.url),
        "posted_at": reel.timestamp.isoformat() if reel.timestamp else None,
        "likes_count": reel.likesCount,
        "comments_count": reel.commentsCount,
        "video_view_count": reel.videoViewCount,
        "video_play_count": reel.videoPlayCount,
        "video_duration_seconds": reel.videoDuration,
        "source_video_url": str(reel.videoUrl),
        "raw_json": reel.model_dump(mode="json"),
    }
    
    if result.data:
        # Обновляем существующий
        reel_id = UUID(result.data[0]["id"])
        supabase.table("reels").update(reel_data).eq("id", str(reel_id)).execute()
        return reel_id
    else:
        # Создаём новый
        result = supabase.table("reels").insert(reel_data).execute()
        return UUID(result.data[0]["id"])

