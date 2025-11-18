"""Visual events detection from video frames."""
import base64
import logging
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import io

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image
import cv2

from services.analyzer_ocr_timed import extract_frame_at_time

logger = logging.getLogger(__name__)

# Используем Claude 3.5 Sonnet для vision анализа (Gemini free модель недоступна)
VISION_MODEL = "anthropic/claude-3.5-sonnet"


def image_to_base64(image: Image.Image) -> str:
    """Конвертирует PIL Image в base64 строку."""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def detect_visual_events(video_path: Path, times: List[float]) -> List[Dict[str, Any]]:
    """Анализирует кадры и определяет визуальные события."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    # Извлекаем кадры
    frames = []
    
    for time in times:
        try:
            frame = extract_frame_at_time(video_path, time)
            frames.append((time, frame))
        except Exception as e:
            logger.warning(f"Не удалось извлечь кадр в {time}s: {e}")
            continue
    
    if not frames:
        return []
    
    # Конвертируем кадры в base64
    image_urls = []
    for time, frame in frames:
        img_b64 = image_to_base64(frame)
        image_urls.append((time, f"data:image/jpeg;base64,{img_b64}"))
    
    system_prompt = """You are analyzing Instagram reel frames to detect visual events.
For each frame, identify:
1. FACE_CLOSEUP - if there's a face in close-up
2. BIG_TEXT - if there's large text covering most of the screen
3. LOGO_OR_BRAND_OBJECT - if there's a logo, brand packaging, or distinctive brand element visible
4. SCENE_CHANGE - if this frame is significantly different from previous

Return JSON array:
[
  {"time": 0.2, "events": ["FACE_CLOSEUP"]},
  {"time": 1.0, "events": ["BIG_TEXT"]},
  ...
]"""
    
    user_prompt = f"""Analyze these {len(frames)} frames at times: {[t for t, _ in frames]}.
Detect visual events: FACE_CLOSEUP, BIG_TEXT, LOGO_OR_BRAND_OBJECT, SCENE_CHANGE.
Return JSON array."""
    
    # Для Gemini объединяем system и user промпты
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    content_parts = [{"type": "text", "text": full_prompt}]
    for time, img_url in image_urls:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": img_url}
        })
    
    messages = [
        {
            "role": "user",
            "content": content_parts
        }
    ]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": VISION_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    
    visual_events = []
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        
        # Детальное логирование ошибки
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenRouter API ошибка {response.status_code}: {error_text}")
            logger.error(f"Payload (первые 500 символов): {json.dumps(payload, indent=2)[:500]}")
            response.raise_for_status()
        
        data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        
        # Парсим JSON
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Ищем JSON массив в ответе (может быть обёрнут в текст)
        # Пробуем найти полный валидный JSON массив
        json_match = None
        
        # Вариант 1: ищем массив с балансом скобок
        bracket_count = 0
        start_idx = content.find('[')
        if start_idx != -1:
            for i in range(start_idx, len(content)):
                if content[i] == '[':
                    bracket_count += 1
                elif content[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_match = content[start_idx:i+1]
                        break
        
        # Вариант 2: если не нашли, пробуем простой regex
        if not json_match:
            json_match_obj = re.search(r'\[[\s\S]*?\]', content)
            if json_match_obj:
                json_match = json_match_obj.group()
        
        if json_match:
            try:
                events_data = json.loads(json_match)
                
                if isinstance(events_data, list):
                    for item in events_data:
                        if isinstance(item, dict):
                            time = item.get("time", 0)
                            events = item.get("events", [])
                            if isinstance(events, list):
                                for event in events:
                                    if isinstance(event, str):
                                        visual_events.append({
                                            "time": round(time, 2),
                                            "event": event
                                        })
                logger.info(f"Успешно распарсено {len(visual_events)} визуальных событий")
            except json.JSONDecodeError as e:
                logger.warning(f"Ошибка парсинга JSON визуальных событий: {e}")
                logger.debug(f"Сырой JSON (первые 300 символов): {json_match[:300]}")
        else:
            logger.warning(f"Не найден JSON массив в ответе. Ответ: {content[:300]}")
    
    logger.info(f"Обнаружено {len(visual_events)} визуальных событий")
    return visual_events

