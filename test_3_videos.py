"""Тестирование анализа на 3 видео."""
import logging
from dotenv import load_dotenv
from uuid import UUID

from services.supabase_client import get_supabase_client
from services.analyzer_raw import analyze_reel_raw

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_3_videos():
    """Тестирует анализ на 3 видео."""
    supabase = get_supabase_client()
    
    # Получаем 3 рилса с видео
    result = supabase.table("reels").select("id").not_.is_("storage_video_path", "null").limit(3).execute()
    
    if not result.data:
        logger.error("Нет рилсов с видео для теста")
        return
    
    reel_ids = [UUID(item["id"]) for item in result.data]
    logger.info(f"Тестирую анализ на {len(reel_ids)} рилсах: {[str(rid)[:8] for rid in reel_ids]}")
    
    success_count = 0
    error_count = 0
    
    for i, reel_id in enumerate(reel_ids, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Тест {i}/{len(reel_ids)}: reel {reel_id}")
        logger.info(f"{'='*60}")
        
        try:
            analyze_reel_raw(reel_id)
            success_count += 1
            logger.info(f"✓ Успешно проанализирован reel {reel_id}")
            
            # Проверяем результат
            analysis = supabase.table("reel_analysis_raw").select(
                "speech_text, screen_text, visual_events, speech_segments, onscreen_text_segments"
            ).eq("reel_id", str(reel_id)).execute()
            
            if analysis.data:
                data = analysis.data[0]
                logger.info(f"  Речь: {len(data.get('speech_text', '') or '')} символов")
                logger.info(f"  Текст: {len(data.get('screen_text', '') or '')} символов")
                
                # Проверяем новые поля
                if data.get('speech_segments'):
                    logger.info(f"  ✓ speech_segments: {len(data['speech_segments'])} сегментов")
                else:
                    logger.warning(f"  ⚠ speech_segments не сохранён (колонка отсутствует?)")
                
                if data.get('visual_events'):
                    logger.info(f"  ✓ visual_events: {len(data['visual_events'])} событий")
                else:
                    logger.warning(f"  ⚠ visual_events не сохранён (колонка отсутствует?)")
            else:
                logger.warning(f"  ⚠ Анализ не найден в БД")
                
        except Exception as e:
            error_count += 1
            logger.error(f"✗ Ошибка анализа reel {reel_id}: {e}", exc_info=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Результаты теста:")
    logger.info(f"  Успешно: {success_count}/{len(reel_ids)}")
    logger.info(f"  Ошибок: {error_count}/{len(reel_ids)}")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    test_3_videos()

