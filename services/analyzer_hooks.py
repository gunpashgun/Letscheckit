"""Hook classification service using OpenRouter LLM."""
import json
import logging
import os
from uuid import UUID
from typing import Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from supabase import Client
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Модель для анализа хуков
LLM_MODEL = "openrouter/auto"  # или "meta-llama/llama-3.1-70b-instruct", "anthropic/claude-3.5-sonnet"

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

USER_PROMPT_TEMPLATE = """Analyze this Instagram reel hook text:

{hook_raw_text}

Return the classification as JSON."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def classify_hook_with_llm(reel_id: UUID) -> None:
    """
    Берёт hook_raw_text для reel_id из reel_analysis_raw,
    вызывает OpenRouter LLM, парсит JSON,
    сохраняет запись в hooks.
    """
    supabase = get_supabase_client()
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    # Получаем hook_raw_text
    result = supabase.table("reel_analysis_raw").select("hook_raw_text").eq("reel_id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не имеет записи в reel_analysis_raw")
    
    hook_raw_text = result.data[0]["hook_raw_text"]
    
    if not hook_raw_text:
        logger.warning(f"Reel {reel_id} имеет пустой hook_raw_text")
        return
    
    logger.info(f"Классификация хука для reel {reel_id}")
    
    # Вызываем OpenRouter API
    user_prompt = USER_PROMPT_TEMPLATE.format(hook_raw_text=hook_raw_text)
    
    response = _call_openrouter(api_key, user_prompt)
    
    # Парсим JSON ответ
    hook_data = _parse_llm_response(response)
    
    # Сохраняем в hooks
    hook_record = {
        "reel_id": str(reel_id),
        "hook_text": hook_data["hook_text"],
        "hook_type": hook_data["hook_type"],
        "tone": hook_data["tone"],
        "starts_with": hook_data["starts_with"],
        "language": hook_data["language"],
        "model_name": LLM_MODEL,
    }
    
    supabase.table("hooks").insert(hook_record).execute()
    logger.info(f"Хук сохранён для reel {reel_id}: {hook_data['hook_type']}")


def _call_openrouter(api_key: str, user_prompt: str) -> str:
    """Вызывает OpenRouter API и возвращает сырой ответ."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Извлекаем текст ответа
        content = data["choices"][0]["message"]["content"]
        logger.debug(f"OpenRouter response: {content}")
        
        return content


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Парсит JSON ответ от LLM, с обработкой ошибок."""
    # Пытаемся найти JSON в ответе
    response_text = response_text.strip()
    
    # Если ответ начинается с ```json или ```, удаляем маркеры
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    response_text = response_text.strip()
    
    try:
        data = json.loads(response_text)
        
        # Валидация обязательных полей
        required_fields = ["hook_text", "hook_type", "tone", "starts_with", "language"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует поле {field} в ответе LLM")
        
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Невалидный JSON от LLM: {response_text}")
        raise ValueError(f"Не удалось распарсить JSON ответ: {e}")

