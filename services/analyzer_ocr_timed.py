"""OCR analysis with timestamps for specific frames."""
import logging
from pathlib import Path
from typing import List, Dict, Any

import cv2
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_frame_at_time(video_path: Path, time: float) -> Image.Image:
    """Извлекает один кадр из видео в указанное время."""
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
    return Image.fromarray(frame_rgb)


def ocr_frame_at_times(video_path: Path, times: List[float]) -> List[Dict[str, Any]]:
    """Извлекает кадры в указанные моменты времени и делает OCR."""
    onscreen_text_segments = []
    
    for time in times:
        try:
            frame = extract_frame_at_time(video_path, time)
            
            try:
                text = pytesseract.image_to_string(frame, lang="ind+eng").strip()
            except:
                try:
                    text = pytesseract.image_to_string(frame, lang="eng").strip()
                except:
                    text = pytesseract.image_to_string(frame).strip()
            
            if text:
                onscreen_text_segments.append({
                    "time": round(time, 2),
                    "text": text
                })
        
        except Exception as e:
            logger.warning(f"Ошибка OCR для кадра в {time}s: {e}")
            continue
    
    logger.info(f"OCR завершён, извлечено {len(onscreen_text_segments)} текстовых сегментов")
    return onscreen_text_segments


