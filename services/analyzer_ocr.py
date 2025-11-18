"""OCR analysis service."""
import logging
from pathlib import Path
from uuid import UUID
import tempfile

import cv2
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_frames(video_path: Path, num_frames: int = 3, start_time: float = 0.0, duration: float = 3.0) -> list[Image.Image]:
    """
    Извлекает кадры из видео.
    Возвращает список PIL Images.
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(start_time * fps)
    end_frame = int((start_time + duration) * fps)
    
    frames = []
    frame_interval = max(1, (end_frame - start_frame) // num_frames)
    
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


def ocr_frames(frames: list[Image.Image]) -> str:
    """
    Применяет OCR к списку кадров.
    Возвращает склеенный текст.
    """
    texts = []
    
    for frame in frames:
        try:
            # Пробуем разные языки (indonesian + english)
            text_id = pytesseract.image_to_string(frame, lang="ind+eng")
            texts.append(text_id.strip())
        except Exception as e:
            logger.warning(f"Ошибка OCR для кадра: {e}")
            # Fallback на английский
            try:
                text_en = pytesseract.image_to_string(frame, lang="eng")
                texts.append(text_en.strip())
            except:
                pass
    
    # Убираем дубликаты и пустые строки
    unique_texts = [t for t in texts if t]
    combined = " ".join(unique_texts)
    
    logger.info(f"OCR извлечено {len(unique_texts)} текстовых блоков")
    return combined

