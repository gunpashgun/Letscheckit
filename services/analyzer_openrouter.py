"""Video and text analysis using OpenRouter vision models."""
import base64
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
import io

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image

logger = logging.getLogger(__name__)

# Vision модель для анализа видео кадров
VISION_MODEL = "openrouter/google/gemini-2.0-flash-exp:free"  # или "anthropic/claude-3.5-sonnet", "openai/gpt-4o"


def extract_frames_from_video(video_path: Path, num_frames: int = 10, start_time: float = 0.0, duration: float = 5.0) -> List[Image.Image]:
    """
    Извлекает кадры из видео используя opencv.
    Возвращает список PIL Images.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError("opencv-python required. Install: pip install opencv-python")
    
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    start_frame = int(start_time * fps)
    end_frame = int((start_time + duration) * fps)
    
    frames = []
    frame_interval = max(1, (end_frame - start_frame) // num_frames) if num_frames > 1 else 1
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    for i in range(num_frames):
        frame_num = start_frame + i * frame_interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # Конвертируем BGR в RGB для PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        frames.append(pil_image)
    
    cap.release()
    return frames


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
def analyze_video_frames_with_openrouter(frames: List[Image.Image], caption: str = "") -> Dict[str, Any]:
    """
    Анализирует кадры видео через OpenRouter vision модель.
    Извлекает текст с экрана (OCR), транскрибирует речь и определяет бренды/рекламу.
    
    Возвращает словарь с:
    - speech_text: транскрипция речи (из субтитров или описание)
    - screen_text: текст с экрана (OCR)
    - brand_mentions: описание упоминаний брендов
    - is_advertisement: является ли это рекламой
    - brand_names: список названий брендов
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment")
    
    # Конвертируем кадры в base64
    image_urls = []
    for frame in frames:
        img_b64 = image_to_base64(frame)
        image_urls.append(f"data:image/jpeg;base64,{img_b64}")
    
    # Формируем промпт
    # Идеальный дизайн
    system_prompt = """You are analyzing Instagram reel frames to extract text content and detect brand mentions/advertising.
Analyze the provided video frames from the first 5 seconds and extract:
1. Any text visible on screen (OCR) - signs, captions, subtitles, text overlays
2. Any speech/subtitle text if visible
3. Brand mentions, brand names, product names visible or mentioned
4. Whether this appears to be an advertisement or sponsored content
5. Any hints/suggestions of brands (logos, product placements, brand colors, etc.)

Return a JSON object with:
- "screen_text": all visible text from the frames (concatenated)
- "speech_text": any speech/subtitle text visible, or description of what is being said/shown
- "brand_mentions": description of any brands/products mentioned or shown (brand names, product names, logos, etc.)
- "is_advertisement": boolean - true if this appears to be an ad/sponsored content/promotional content
- "brand_names": array of brand/product names found (e.g., ["Nike", "Coca-Cola", "iPhone"])

Focus on Indonesian (Bahasa Indonesia) and English text. Be thorough in detecting brand mentions, even subtle ones."""
    
    user_prompt = f"""Analyze these {len(frames)} video frames from the first 5 seconds of an Instagram reel.

Caption context: {caption[:200] if caption else "No caption"}

Extract all visible text, speech/subtitle text, and detect any brand mentions or advertising.
Pay special attention to:
- Brand logos, product names, company names
- Sponsored content indicators (#ad, #sponsored, #partnership)
- Product placements
- Brand colors, packaging, or distinctive brand elements
- Any hints that this is promotional/advertising content

Return JSON:
{{
  "screen_text": "all visible text from frames",
  "speech_text": "speech/subtitle text or description",
  "brand_mentions": "detailed description of brands/products mentioned or shown",
  "is_advertisement": true/false,
  "brand_names": ["brand1", "brand2", ...]
}}"""
    
    # Формируем сообщения для vision модели
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Добавляем кадры в сообщение
    content_parts = [{"type": "text", "text": user_prompt}]
    for img_url in image_urls:
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
        "HTTP-Referer": "https://github.com/your-repo",  # Опционально
    }
    
    payload = {
        "model": VISION_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        logger.debug(f"OpenRouter vision response: {content[:200]}...")
        
        # Парсим JSON из ответа
        import json
        import re
        
        # Пытаемся найти JSON в ответе (более надежный способ)
        content = content.strip()
        
        # Убираем markdown code blocks если есть
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Ищем JSON объект
        json_match = re.search(r'\{.*?"screen_text".*?"speech_text".*?\}', content, re.DOTALL)
        if not json_match:
            # Пробуем найти любой JSON объект
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        
        if json_match:
            try:
                result = json.loads(json_match.group())
                return {
                    "screen_text": result.get("screen_text", ""),
                    "speech_text": result.get("speech_text", ""),
                    "brand_mentions": result.get("brand_mentions", ""),
                    "is_advertisement": result.get("is_advertisement", False),
                    "brand_names": result.get("brand_names", []),
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Ошибка парсинга JSON: {e}")
        
        # Fallback: если JSON не найден, пытаемся извлечь текст
        logger.warning("Не удалось распарсить JSON из ответа, используем fallback")
        return {
            "screen_text": content[:500],
            "speech_text": "",
            "brand_mentions": "",
            "is_advertisement": False,
            "brand_names": [],
        }

