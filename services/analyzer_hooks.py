"""Hook analysis service using OpenRouter LLM."""
import json
import os
import httpx
from typing import Dict, Any
from uuid import UUID
from tenacity import retry, stop_after_attempt, wait_exponential
from supabase import Client

from services.supabase_client import get_supabase_client


# Константы для LLM
OPENROUTER_MODEL = "openrouter/auto"  # или "meta-llama/llama-3.1-70b-instruct"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


SYSTEM_PROMPT = """You are an Indonesian Instagram hooks analyzer. Your task is to analyze hook text from Instagram reels and classify it into categories.

Analyze the provided hook text and return a JSON object with the following structure:
{
  "hook_text": "string, normalized hook text, max 160 characters",
  "hook_type": "QUESTION | PAIN_POINT | BIG_PROMISE | PATTERN_INTERRUPT | STORY_PERSONAL | AUTHORITY_PROOF | HOW_TO | FOMO_URGENCY | OTHER",
  "tone": "FRIENDLY | SERIOUS | URGENT | FUNNY | EMPATHETIC | NEUTRAL",
  "starts_with": "QUESTION | NUMBER | STATEMENT | VISUAL_ONLY",
  "language": "id | en | mix"
}

Return ONLY valid JSON, no additional text."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def classify_hook_with_llm(reel_id: UUID) -> None:
    """
    Берёт hook_raw_text для reel_id из reel_analysis_raw,
    вызывает OpenRouter LLM, парсит JSON,
    сохраняет запись в hooks.
    """
    supabase = get_supabase_client()
    
    # Проверяем, есть ли уже хук для этого рилса
    existing = supabase.table("hooks").select("id").eq("reel_id", str(reel_id)).execute()
    if existing.data:
        print(f"Reel {reel_id} already has hook classification, skipping")
        return
    
    # Получаем hook_raw_text
    result = supabase.table("reel_analysis_raw").select("hook_raw_text").eq("reel_id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"No raw analysis found for reel {reel_id}")
    
    hook_raw_text = result.data[0]["hook_raw_text"]
    
    if not hook_raw_text or not hook_raw_text.strip():
        print(f"Empty hook_raw_text for reel {reel_id}, skipping")
        return
    
    # Вызываем LLM
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    response = _call_openrouter(hook_raw_text, api_key)
    
    # Парсим JSON ответ
    hook_data = _parse_llm_response(response, reel_id)
    
    # Сохраняем в hooks
    hook_record = {
        "reel_id": str(reel_id),
        "hook_text": hook_data["hook_text"],
        "hook_type": hook_data["hook_type"],
        "tone": hook_data["tone"],
        "starts_with": hook_data["starts_with"],
        "language": hook_data["language"],
        "model_name": OPENROUTER_MODEL,
    }
    
    supabase.table("hooks").insert(hook_record).execute()
    
    print(f"Classified hook for reel {reel_id}: {hook_data['hook_type']}")


def _call_openrouter(hook_text: str, api_key: str) -> str:
    """Вызывает OpenRouter API и возвращает ответ."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # Опционально
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": hook_text},
        ],
        "temperature": 0.3,
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_llm_response(response_text: str, reel_id: UUID) -> Dict[str, Any]:
    """Парсит JSON ответ от LLM, с обработкой ошибок."""
    # Пытаемся извлечь JSON из ответа (на случай если LLM добавил текст)
    response_text = response_text.strip()
    
    # Ищем JSON объект
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}") + 1
    
    if start_idx == -1 or end_idx == 0:
        raise ValueError(f"Invalid LLM response format for reel {reel_id}: {response_text}")
    
    json_str = response_text[start_idx:end_idx]
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error for reel {reel_id}: {e}")
        print(f"Response text: {response_text}")
        raise
    
    # Валидация полей
    required_fields = ["hook_text", "hook_type", "tone", "starts_with", "language"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing field '{field}' in LLM response for reel {reel_id}")
    
    # Обрезаем hook_text до 160 символов
    if len(data["hook_text"]) > 160:
        data["hook_text"] = data["hook_text"][:160]
    
    return data


def classify_all_pending_hooks() -> None:
    """Классифицирует хуки для всех рилсов с raw-анализом, но без hooks."""
    supabase = get_supabase_client()
    
    # Находим рилсы с raw-анализом, но без hooks
    result = supabase.table("reel_analysis_raw").select("reel_id").execute()
    
    reel_ids_with_raw = {UUID(row["reel_id"]) for row in result.data}
    
    hooks_result = supabase.table("hooks").select("reel_id").execute()
    reel_ids_with_hooks = {UUID(row["reel_id"]) for row in hooks_result.data}
    
    pending_reel_ids = reel_ids_with_raw - reel_ids_with_hooks
    
    print(f"Found {len(pending_reel_ids)} reels pending hook classification")
    
    for reel_id in pending_reel_ids:
        try:
            classify_hook_with_llm(reel_id)
        except Exception as e:
            print(f"Error classifying hook for reel {reel_id}: {e}")
            continue

