"""Ingestion service for Apify JSON data."""
import json
from typing import List
from uuid import UUID
from supabase import Client

from models.apify_reel import ApifyReel
from services.supabase_client import get_supabase_client


def ingest_apify_json(path: str) -> List[UUID]:
    """
    Читает JSON-файл с массивом рилсов от Apify.
    Создаёт/обновляет записи в creators и reels.
    Возвращает список reel_id (UUID) в нашей БД.
    """
    supabase = get_supabase_client()
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("JSON должен содержать массив объектов")
    
    reel_ids = []
    
    for item in data:
        reel = ApifyReel(**item)
        reel_id = _process_reel(supabase, reel)
        reel_ids.append(reel_id)
    
    return reel_ids


def _process_reel(supabase: Client, reel: ApifyReel) -> UUID:
    """Обрабатывает один рилс: создаёт/обновляет creator и reel."""
    # Создать или найти creator
    creator_id = _get_or_create_creator(supabase, reel)
    
    # Создать или обновить reel
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
    """Находит или создаёт reel по ig_reel_id."""
    # Проверяем существование
    result = supabase.table("reels").select("id").eq("ig_reel_id", reel.id).execute()
    
    if result.data:
        reel_uuid = UUID(result.data[0]["id"])
        # Обновляем данные
        update_data = {
            "shortcode": reel.shortCode,
            "creator_id": str(creator_id),
            "caption": reel.caption,
            "hashtags": reel.hashtags,
            "url": str(reel.url),
            "posted_at": reel.timestamp.isoformat(),
            "likes_count": reel.likesCount,
            "comments_count": reel.commentsCount,
            "video_view_count": reel.videoViewCount,
            "video_play_count": reel.videoPlayCount,
            "video_duration_seconds": reel.videoDuration,
            "source_video_url": str(reel.videoUrl),
            "raw_json": reel.model_dump(),
        }
        supabase.table("reels").update(update_data).eq("id", str(reel_uuid)).execute()
        return reel_uuid
    
    # Создаём новый
    reel_data = {
        "ig_reel_id": reel.id,
        "shortcode": reel.shortCode,
        "creator_id": str(creator_id),
        "caption": reel.caption,
        "hashtags": reel.hashtags,
        "url": str(reel.url),
        "posted_at": reel.timestamp.isoformat(),
        "likes_count": reel.likesCount,
        "comments_count": reel.commentsCount,
        "video_view_count": reel.videoViewCount,
        "video_play_count": reel.videoPlayCount,
        "video_duration_seconds": reel.videoDuration,
        "source_video_url": str(reel.videoUrl),
        "raw_json": reel.model_dump(),
    }
    
    result = supabase.table("reels").insert(reel_data).execute()
    return UUID(result.data[0]["id"])

