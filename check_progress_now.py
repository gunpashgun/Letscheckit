#!/usr/bin/env python3
"""Quick progress check."""
import os
import sys
from pathlib import Path

# Добавляем путь
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем переменные окружения вручную
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print('❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY')
    sys.exit(1)

try:
    supabase = create_client(url, key)
    
    # Всего рилсов
    total_result = supabase.table('reels').select('id', count='exact').execute()
    total_count = total_result.count if hasattr(total_result, 'count') else len(total_result.data) if total_result.data else 0
    
    # Скачано
    downloaded_result = supabase.table('reels').select('id', count='exact').not_.is_('storage_video_path', 'null').execute()
    downloaded_count = downloaded_result.count if hasattr(downloaded_result, 'count') else len(downloaded_result.data) if downloaded_result.data else 0
    
    # Осталось
    pending_count = total_count - downloaded_count
    percentage = (downloaded_count / total_count * 100) if total_count > 0 else 0
    
    print('\n' + '='*50)
    print('📊 Текущий прогресс скачивания')
    print('='*50)
    print(f'Всего рилсов:        {total_count}')
    print(f'✅ Скачано:           {downloaded_count}')
    print(f'⏳ Осталось:          {pending_count}')
    print(f'📈 Прогресс:          {percentage:.2f}%')
    print('='*50)
    
    if total_count > 0:
        bar_length = 40
        filled = int(bar_length * percentage / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f'[{bar}] {percentage:.2f}%\n')
    
    if downloaded_count > 0 and pending_count > 0:
        print(f'📥 Обработано: {downloaded_count} из {total_count}')
        print(f'⏱️  Осталось: {pending_count} видео\n')
        
except Exception as e:
    print(f'❌ Ошибка: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

