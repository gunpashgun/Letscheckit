"""OCR analysis service."""
import cv2
import pytesseract
from typing import List
from pathlib import Path


def extract_frames_ocr(video_path: str, num_frames: int = 3, start_time: float = 0.0, end_time: float = 3.0) -> str:
    """
    Извлекает текст с экрана из первых кадров видео через OCR.
    
    Args:
        video_path: путь к видеофайлу
        num_frames: количество кадров для обработки
        start_time: начало временного диапазона (секунды)
        end_time: конец временного диапазона (секунды)
    
    Returns:
        Склеенный текст со всех кадров
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    start_frame = int(start_time * fps)
    end_frame = min(int(end_time * fps), total_frames)
    
    frame_indices = []
    if num_frames == 1:
        frame_indices = [start_frame]
    else:
        step = (end_frame - start_frame) / (num_frames - 1)
        frame_indices = [int(start_frame + i * step) for i in range(num_frames)]
    
    texts = []
    
    for frame_idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        # Конвертируем в RGB для pytesseract
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Извлекаем текст
        try:
            text = pytesseract.image_to_string(frame_rgb, lang="ind+eng")
            if text.strip():
                texts.append(text.strip())
        except Exception as e:
            print(f"OCR error on frame {frame_idx}: {e}")
            continue
    
    cap.release()
    
    return " | ".join(texts).strip()

