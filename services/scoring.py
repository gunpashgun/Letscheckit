"""Scoring service for reels."""
import logging
import math
from uuid import UUID
from typing import Optional

from supabase import Client
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def update_reel_scores(reel_id: UUID, followers: Optional[int] = None) -> None:
    """
    Считает engagement_rate и hook_score для одного рилса
    и обновляет соответствующие поля в reels.
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select(
        "likes_count, comments_count, video_play_count, video_view_count, creator_id"
    ).eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не найден в БД")
    
    reel_data = result.data[0]
    likes = reel_data.get("likes_count", 0) or 0
    comments = reel_data.get("comments_count", 0) or 0
    plays = reel_data.get("video_play_count") or reel_data.get("video_view_count") or 0
    creator_id = reel_data.get("creator_id")
    
    # Если followers не передан, пытаемся получить из creators
    if followers is None and creator_id:
        creator_result = supabase.table("creators").select("followers").eq("id", creator_id).execute()
        
        if creator_result.data:
            followers = creator_result.data[0].get("followers")
    
    # 1. Engagement Rate
    if plays > 0:
        engagement_rate = (likes + comments) / plays
    else:
        engagement_rate = 0.0
    
    # 2. Account weight
    if followers and followers > 0:
        account_weight = 1 / math.log10(followers + 10_000)
    else:
        account_weight = 1.0
    
    # 3. Hook score (более сложная формула)
    if plays > 0 and followers and followers > 0:
        # ER * (plays / followers) ** 0.3 * account_weight
        hook_score = engagement_rate * (plays / followers) ** 0.3 * account_weight
    elif plays > 0:
        # Если нет followers, используем упрощённую формулу
        hook_score = engagement_rate * account_weight
    else:
        hook_score = 0.0
    
    logger.info(
        f"Reel {reel_id}: ER={engagement_rate:.4f}, "
        f"account_weight={account_weight:.4f}, hook_score={hook_score:.4f}"
    )
    
    # Обновляем в БД
    supabase.table("reels").update({
        "engagement_rate": engagement_rate,
        "hook_score": hook_score,
    }).eq("id", str(reel_id)).execute()

