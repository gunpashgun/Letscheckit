"""Scoring service for reels."""
import math
from uuid import UUID
from typing import Optional
from supabase import Client

from services.supabase_client import get_supabase_client


def update_reel_scores(reel_id: UUID, followers: Optional[int] = None) -> None:
    """
    Считает engagement_rate и hook_score для одного рилса
    и обновляет соответствующие поля в reels.
    """
    supabase = get_supabase_client()
    
    # Получаем данные рилса
    result = supabase.table("reels").select("*").eq("id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} not found")
    
    reel = result.data[0]
    
    # Получаем метрики
    likes = reel.get("likes_count") or 0
    comments = reel.get("comments_count") or 0
    plays = reel.get("video_play_count") or reel.get("video_view_count") or 0
    
    # Считаем engagement rate
    if plays > 0:
        engagement_rate = (likes + comments) / plays
    else:
        engagement_rate = 0.0
    
    # Считаем account_weight
    if followers and followers > 0:
        account_weight = 1 / math.log10(followers + 10_000)
    else:
        account_weight = 1.0
    
    # Финальный hook_score
    # Вариант 1: простой
    hook_score = engagement_rate * account_weight
    
    # Вариант 2: посложнее (раскомментируйте если нужно)
    # if followers and followers > 0:
    #     hook_score = engagement_rate * (plays / followers) ** 0.3 * account_weight
    # else:
    #     hook_score = engagement_rate * account_weight
    
    # Обновляем в БД
    supabase.table("reels").update({
        "engagement_rate": engagement_rate,
        "hook_score": hook_score,
    }).eq("id", str(reel_id)).execute()
    
    print(f"Updated scores for reel {reel_id}: ER={engagement_rate:.4f}, Score={hook_score:.4f}")


def update_all_scores(followers_map: Optional[dict[UUID, int]] = None) -> None:
    """
    Обновляет метрики для всех рилсов.
    
    Args:
        followers_map: словарь {reel_id: followers_count} для каждого рилса.
                      Если None, используется followers из таблицы creators.
    """
    supabase = get_supabase_client()
    
    result = supabase.table("reels").select("id, creator_id").execute()
    
    reel_ids = [UUID(row["id"]) for row in result.data]
    creator_ids = {UUID(row["id"]): UUID(row["creator_id"]) for row in result.data}
    
    print(f"Found {len(reel_ids)} reels to update scores")
    
    # Если followers_map не передан, пытаемся получить из creators
    if followers_map is None:
        followers_map = {}
        for reel_id, creator_id in creator_ids.items():
            creator_result = supabase.table("creators").select("followers").eq("id", str(creator_id)).execute()
            if creator_result.data and creator_result.data[0].get("followers"):
                followers_map[reel_id] = creator_result.data[0]["followers"]
    
    for reel_id in reel_ids:
        followers = followers_map.get(reel_id)
        try:
            update_reel_scores(reel_id, followers)
        except Exception as e:
            print(f"Error updating scores for reel {reel_id}: {e}")
            continue

