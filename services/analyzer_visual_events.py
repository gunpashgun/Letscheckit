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

logger = logging.getLogger(__name__)

# Vision модель для анализа визуальных событий
VISION_MODEL = "openrouter/google/gemini-2.0-flash-exp:free"


def image_to_base64(image: Image.Image) -> str:
    """Конвертирует PIL Image в base64 строку."""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def detect_visual_events(video_path: Path, times: List[float]) -> List[Dict[str, Any]]:
    """
    Анализирует кадры в указанные моменты времени и определяет визуальные события.
    Возвращает список {time, event}.
    
    События:
    - FACE_CLOSEUP: лицо крупным планом
    - BIG_TEXT: крупный текст на весь экран
    - SCENE_CHANGE: резкая смена сцены (определяется сравнением соседних кадров)
    - LOGO_OR_BRAND_OBJECT: объект, похожий на логотип/упаковку
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    # Извлекаем кадры
    frames = []
    for time in times:
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise RuntimeError(f"Не удалось открыть видео: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_num = int(time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                raise RuntimeError(f"Не удалось извлечь кадр в момент {time}s")
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            frames.append((time, pil_image))
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
    
    # Формируем промпт для определения визуальных событий
    system_prompt = """You are analyzing Instagram reel frames to detect visual events.
For each frame, identify:
1. FACE_CLOSEUP - if there's a face in close-up (occupies significant portion of frame)
2. BIG_TEXT - if there's large text covering most of the screen
3. LOGO_OR_BRAND_OBJECT - if there's a logo, brand packaging, or distinctive brand element visible
4. SCENE_CHANGE - if this frame is significantly different from previous (only for frames after first)

Return JSON array with events detected for each frame:
[
  {"time": 0.2, "events": ["FACE_CLOSEUP"]},
  {"time": 1.0, "events": ["BIG_TEXT", "LOGO_OR_BRAND_OBJECT"]},
  ...
]

Only include events that are clearly present. Be conservative."""
    
    user_prompt = f"""Analyze these {len(frames)} frames from an Instagram reel at times: {[t for t, _ in frames]}.

For each frame, detect visual events:
- FACE_CLOSEUP: face in close-up
- BIG_TEXT: large text on screen
- LOGO_OR_BRAND_OBJECT: logos, brand packaging, brand elements
- SCENE_CHANGE: significant scene change (compare with previous frame)

Return JSON array:
[
  {{"time": 0.2, "events": ["FACE_CLOSEUP"]}},
  {{"time": 1.0, "events": ["BIG_TEXT"]}},
  ...
]"""
    
    # Формируем сообщения для vision модели
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Добавляем кадры в сообщение
    content_parts = [{"type": "text", "text": user_prompt}]
    for time, img_url in image_urls:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": img_url}
        })
    
    messages.append({
        "role": "user",
        "content": content_parts
    })
    
    # Вызываем OpenRouter API
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
        response.raise_for_status()
        data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        logger.debug(f"Visual events response: {content[:200]}...")
        
        # Парсим JSON из ответа
        content = content.strip()
        
        # Убираем markdown code blocks если есть
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Ищем JSON массив
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        
        if json_match:
            try:
                events_data = json.loads(json_match.group())
                # Преобразуем формат: из [{time, events}] в [{time, event}]
                for item in events_data:
                    time = item.get("time", 0)
                    events = item.get("events", [])
                    for event in events:
                        visual_events.append({
                            "time": round(time, 2),
                            "event": event
                        })
            except json.JSONDecodeError as e:
                logger.warning(f"Ошибка парсинга JSON визуальных событий: {e}")
    
    logger.info(f"Обнаружено {len(visual_events)} визуальных событий")
    
    return visual_events

