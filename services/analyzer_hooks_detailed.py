"""Detailed hook and brand analysis using LLM with structured output."""
import json
import logging
import os
import re
from uuid import UUID
from typing import List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from supabase import Client
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Модель для анализа хуков и брендов
LLM_MODEL = "openrouter/auto"  # или конкретная модель

SYSTEM_PROMPT = """You are an expert Instagram reel analyzer specializing in hook detection and brand/advertising analysis.

Analyze the provided reel context and return structured JSON with:
1. An array of hooks detected in the reel (can be multiple hooks)
2. Brand/advertising information

Be thorough and accurate. Focus on Indonesian (Bahasa Indonesia) and English content."""

USER_PROMPT_TEMPLATE = """Analyze this Instagram reel context:

{analysis_context}

Return JSON with this exact structure:
{{
  "hooks": [
    {{
      "time_start": 0.0,
      "time_end": 1.2,
      "channel": "VOICE | TEXT | VISUAL | MIX",
      "hook_text": "normalized hook text, max 160 chars",
      "hook_type": "QUESTION | PAIN_POINT | BIG_PROMISE | PATTERN_INTERRUPT | STORY | AUTHORITY | HOW_TO | FOMO | OTHER",
      "strength": 1-10,
      "starts_with": "QUESTION | NUMBER | STATEMENT | VISUAL_ONLY"
    }}
  ],
  "brand_analysis": {{
    "has_brand_mention": true/false,
    "brand_names": ["Brand X", "Brand Y"],
    "brand_sources": ["SPEECH", "ONSCREEN_TEXT", "MENTION_OR_TAG", "CAPTION", "VISUAL_LOGO"],
    "is_probable_ad": true/false,
    "ad_type": "BRAND_POST | SPONSORSHIP | UGC_LIKE_AD | ORGANIC_CONTENT",
    "ad_description": "brief description",
    "brand_confidence": 0.0-1.0,
    "ad_confidence": 0.0-1.0
  }}
}}

Rules:
- hooks: can be multiple hooks, each with time_start/time_end from speech_segments, onscreen_text_segments, or visual_events
- channel: VOICE if from speech_segments, TEXT if from onscreen_text_segments, VISUAL if from visual_events, MIX if combined
- brand_sources: array indicating where brands were found
- Return ONLY valid JSON, no additional text."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def analyze_hooks_and_brands(reel_id: UUID) -> None:
    """
    Берёт analysis_context из reel_analysis_raw,
    вызывает OpenRouter LLM для детального анализа хуков и брендов,
    сохраняет результаты в hooks и reels.
    """
    supabase = get_supabase_client()
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    # Получаем analysis_context
    result = supabase.table("reel_analysis_raw").select("analysis_context").eq("reel_id", str(reel_id)).execute()
    
    if not result.data:
        raise ValueError(f"Reel {reel_id} не имеет записи в reel_analysis_raw")
    
    analysis_context = result.data[0].get("analysis_context")
    
    if not analysis_context:
        logger.warning(f"Reel {reel_id} не имеет analysis_context")
        return
    
    logger.info(f"Детальный анализ хуков и брендов для reel {reel_id}")
    
    # Формируем промпт
    user_prompt = USER_PROMPT_TEMPLATE.format(
        analysis_context=json.dumps(analysis_context, indent=2, ensure_ascii=False)
    )
    
    # Вызываем OpenRouter API
    response_text = _call_openrouter(api_key, user_prompt)
    
    # Парсим JSON ответ
    analysis_result = _parse_llm_response(response_text)
    
    hooks = analysis_result.get("hooks", [])
    brand_analysis = analysis_result.get("brand_analysis", {})
    
    logger.info(f"Найдено {len(hooks)} хуков, brand_mention={brand_analysis.get('has_brand_mention', False)}")
    
    # Сохраняем хуки (может быть несколько на один рилс)
    for hook in hooks:
        hook_record = {
            "reel_id": str(reel_id),
            "time_start": hook.get("time_start"),
            "time_end": hook.get("time_end"),
            "channel": hook.get("channel"),
            "hook_text": hook.get("hook_text"),
            "hook_type": hook.get("hook_type"),
            "tone": "NEUTRAL",  # можно добавить в промпт
            "starts_with": hook.get("starts_with"),
            "language": "id",  # можно определить из контекста
            "model_name": LLM_MODEL,
            "strength": hook.get("strength"),
        }
        
        supabase.table("hooks").insert(hook_record).execute()
    
    # Сохраняем информацию о брендах в reels
    brand_update = {
        "has_brand_mention": brand_analysis.get("has_brand_mention", False),
        "brand_names": brand_analysis.get("brand_names", []),
        "brand_sources": brand_analysis.get("brand_sources", []),
        "is_probable_ad": brand_analysis.get("is_probable_ad", False),
        "ad_type": brand_analysis.get("ad_type"),
        "ad_description": brand_analysis.get("ad_description"),
        "brand_confidence": brand_analysis.get("brand_confidence"),
        "ad_confidence": brand_analysis.get("ad_confidence"),
    }
    
    supabase.table("reels").update(brand_update).eq("id", str(reel_id)).execute()
    
    logger.info(f"Анализ сохранён для reel {reel_id}")


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
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        logger.debug(f"OpenRouter response: {content[:500]}...")
        
        return content


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Парсит JSON ответ от LLM."""
    response_text = response_text.strip()
    
    # Убираем markdown code blocks если есть
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    response_text = response_text.strip()
    
    # Ищем JSON объект
    json_match = re.search(r'\{.*?"hooks".*?"brand_analysis".*?\}', response_text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
    
    if json_match:
        try:
            data = json.loads(json_match.group())
            
            # Валидация структуры
            if "hooks" not in data:
                data["hooks"] = []
            if "brand_analysis" not in data:
                data["brand_analysis"] = {}
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.error(f"Ответ: {response_text[:500]}")
            raise ValueError(f"Не удалось распарсить JSON ответ: {e}")
    
    raise ValueError("Не найден JSON объект в ответе LLM")

