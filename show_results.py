#!/usr/bin/env python3
"""Show analysis results."""
import os
from pathlib import Path
import sys
import json

sys.path.insert(0, '.')

# Load env
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print('❌ Не найдены переменные окружения')
    sys.exit(1)

supabase = create_client(url, key)

# Получаем последние проанализированные рилсы
results = supabase.table('reel_analysis_raw').select('*, reels(caption, url, likes_count, video_play_count, ownerUsername:creators(username))').order('created_at', desc=True).limit(5).execute()

print('\n' + '='*80)
print('📊 РЕЗУЛЬТАТЫ АНАЛИЗА (последние 5 рилсов)')
print('='*80 + '\n')

if results.data:
    for idx, item in enumerate(results.data, 1):
        reel_info = item.get('reels', {}) if isinstance(item.get('reels'), dict) else {}
        
        print(f'🎬 РИЛС #{idx}')
        print('-' * 80)
        print(f'Reel ID: {item.get("reel_id", "N/A")}')
        print(f'URL: {reel_info.get("url", "N/A")}')
        print(f'Likes: {reel_info.get("likes_count", "N/A")} | Plays: {reel_info.get("video_play_count", "N/A")}')
        
        caption = reel_info.get("caption", "")
        if caption:
            print(f'Caption: {caption[:150]}...' if len(caption) > 150 else f'Caption: {caption}')
        print()
        
        print('📝 SPEECH TEXT (ASR - транскрипция аудио):')
        speech = item.get('speech_text', '')
        if speech:
            print(f'  {speech[:250]}...' if len(speech) > 250 else f'  {speech}')
        else:
            print('  Нет данных')
        print()
        
        print('📱 SCREEN TEXT (OCR - текст с экрана):')
        screen = item.get('screen_text', '')
        if screen:
            print(f'  {screen[:250]}...' if len(screen) > 250 else f'  {screen}')
        else:
            print('  Нет данных')
        print()
        
        print('💬 CAPTION HOOK (первые строки caption):')
        caption_hook = item.get('caption_hook_text', '')
        if caption_hook:
            print(f'  {caption_hook[:200]}...' if len(caption_hook) > 200 else f'  {caption_hook}')
        else:
            print('  Нет данных')
        print()
        
        print('🔗 HOOK RAW TEXT (объединенный текст для LLM):')
        hook_raw = item.get('hook_raw_text', '')
        if hook_raw:
            print(f'  {hook_raw[:300]}...' if len(hook_raw) > 300 else f'  {hook_raw}')
        else:
            print('  Нет данных')
        print()
        
        # Проверяем структурированные данные
        if item.get('speech_segments'):
            segs = item['speech_segments']
            if isinstance(segs, list):
                print(f'📊 Speech segments: {len(segs)} сегментов')
                if segs:
                    print(f'   Пример: "{segs[0].get("text", "")[:50]}..." (start: {segs[0].get("start", 0)}, end: {segs[0].get("end", 0)})')
        
        if item.get('onscreen_text_segments'):
            segs = item['onscreen_text_segments']
            if isinstance(segs, list):
                print(f'📊 Onscreen text segments: {len(segs)} сегментов')
        
        if item.get('visual_events'):
            events = item['visual_events']
            if isinstance(events, list):
                print(f'📊 Visual events: {len(events)} событий')
        
        print(f'Created: {item.get("created_at", "N/A")}')
        print('='*80 + '\n')
else:
    print('❌ Нет проанализированных рилсов\n')

# Статистика
total = supabase.table('reel_analysis_raw').select('id', count='exact').execute()
total_count = total.count if hasattr(total, 'count') else len(total.data) if total.data else 0

print(f'\n📈 Всего проанализировано: {total_count} рилсов\n')

# Статистика по полям
if total_count > 0:
    all_results = supabase.table('reel_analysis_raw').select('speech_text, screen_text, caption_hook_text, hook_raw_text').limit(100).execute()
    
    if all_results.data:
        has_speech = sum(1 for r in all_results.data if r.get('speech_text'))
        has_screen = sum(1 for r in all_results.data if r.get('screen_text'))
        has_caption = sum(1 for r in all_results.data if r.get('caption_hook_text'))
        has_hook = sum(1 for r in all_results.data if r.get('hook_raw_text'))
        sample_size = len(all_results.data)
        
        print('📊 СТАТИСТИКА ПО ПОЛЯМ:')
        print(f'  ✅ Speech text: {has_speech}/{sample_size} ({has_speech/sample_size*100:.1f}%)')
        print(f'  ✅ Screen text: {has_screen}/{sample_size} ({has_screen/sample_size*100:.1f}%)')
        print(f'  ✅ Caption hook: {has_caption}/{sample_size} ({has_caption/sample_size*100:.1f}%)')
        print(f'  ✅ Hook raw: {has_hook}/{sample_size} ({has_hook/sample_size*100:.1f}%)\n')

