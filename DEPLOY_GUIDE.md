# Инструкция по деплою Apify актора

## Шаг 1: Подготовка актора в Apify Console

### 1.1 Откройте ваш актор
Перейдите по ссылке:
```
https://console.apify.com/organization/MLuL6fSrXc3YfYDhQ/actors/DRPr1b1S4f7LehPKg/source
```

### 1.2 Загрузите код
В разделе **Source** выберите один из вариантов:

#### Вариант A: GitHub (рекомендуется)
1. Создайте репозиторий на GitHub
2. Загрузите все файлы из папки `apify_actor/`
3. В Apify Console:
   - Source type: **GitHub**
   - Repository: `username/repo-name`
   - Branch: `main`

#### Вариант B: Прямая загрузка
1. В Apify Console выберите Source type: **Web IDE**
2. Скопируйте содержимое каждого файла:
   - `main.js`
   - `package.json`
   - `INPUT_SCHEMA.json`
   - `.actor/actor.json`
   - `Dockerfile`
   - `README.md`

## Шаг 2: Настройка окружения

### 2.1 Environment Variables
Перейдите в **Settings → Environment variables** и добавьте:

```
OPENROUTER_API_KEY = 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
```

⚠️ **Важно**: Используйте Secrets для безопасного хранения API ключа!

### 2.2 Memory & Timeout
В **Settings**:
- Memory: **2048 MB** (рекомендуется для обработки видео)
- Timeout: **300 seconds** (5 минут достаточно для анализа)

### 2.3 Build settings
- Build tag: `latest`
- Base Docker image: `apify/actor-node:18` (указано в Dockerfile)

## Шаг 3: Build актора

1. Нажмите **Build**
2. Дождитесь завершения (обычно 2-5 минут)
3. Проверьте логи - не должно быть ошибок

## Шаг 4: Тестовый запуск

### 4.1 Подготовьте тестовый Input

Перейдите в **Input** и вставьте:

```json
{
  "reel_id": "test-reel-123",
  "video_url": "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/test/video.mp4",
  "caption": "Test reel for analysis",
  "hashtags": ["#test", "#demo"],
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

⚠️ **Замените `video_url`** на реальный URL видео из вашего Supabase Storage!

### 4.2 Запустите актора
1. Нажмите **Start**
2. Следите за логами в реальном времени

### 4.3 Ожидаемый результат

Вы должны увидеть в логах:
```
INFO Начало анализа рилса: test-reel-123
INFO Video URL: https://...
INFO Скачивание видео...
INFO Видео скачано: /tmp/video_xxx.mp4
INFO Извлечение аудио (5s)...
INFO Аудио извлечено: /tmp/video_xxx.wav
INFO ASR анализ через OpenRouter...
INFO Распознано 3 сегментов речи
INFO OCR анализ через OpenRouter...
INFO Извлечено 4 текстовых сегментов
INFO Анализ визуальных событий через OpenRouter...
INFO Обнаружено 5 визуальных событий
INFO ✅ Анализ завершён успешно!
```

### 4.4 Проверьте результаты
Перейдите в **Storage → Dataset** и проверьте:
```json
{
  "reel_id": "test-reel-123",
  "speech_segments": [...],
  "onscreen_text_segments": [...],
  "visual_events": [...],
  "metadata": {...}
}
```

## Шаг 5: Интеграция с вашим кодом

### 5.1 Установите Apify token в .env

Получите API token:
1. Перейдите в [Settings → Integrations](https://console.apify.com/account/integrations)
2. Скопируйте **Personal API token**

Добавьте в `.env`:
```bash
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxx
APIFY_ACTOR_ID=DRPr1b1S4f7LehPKg
```

### 5.2 Тестовый запуск через Python

```bash
# Анализ одного рилса
python main.py analyze-via-apify --limit 1

# Анализ всех рилсов (параллельно, 5 акторов одновременно)
python main.py analyze-via-apify --workers 5
```

### 5.3 Проверьте результаты в БД

```bash
python3 -c "
from services.supabase_client import get_supabase_client
supabase = get_supabase_client()
result = supabase.table('reel_analysis_raw').select('*').limit(1).execute()
print(result.data)
"
```

## Шаг 6: Мониторинг и оптимизация

### 6.1 Мониторинг запусков
- Перейдите в **Runs** - видны все запуски
- Проверяйте **Duration** и **Cost**

### 6.2 Оптимизация стоимости

**Если анализ слишком дорогой:**
- Уменьшите `analysis_window_seconds` (с 5 до 3 секунд)
- Уменьшите количество `ocr_times` (с 5 до 3 кадров)
- Используйте более дешёвые модели в `main.js`

**Если анализ слишком медленный:**
- Увеличьте Memory в Settings (до 4096 MB)
- Используйте параллельные запуски через `--workers`

### 6.3 Логирование

Добавьте больше логов для отладки:
```javascript
Actor.log.info('Промежуточный результат:', someData);
Actor.log.warning('Предупреждение:', warning);
Actor.log.error('Ошибка:', error);
```

## Troubleshooting

### Ошибка "Build failed"
- Проверьте синтаксис в `package.json`
- Убедитесь что все файлы на месте
- Проверьте логи Build

### Ошибка "Failed to download video"
- Проверьте доступность `video_url`
- Если Supabase bucket приватный, сделайте его публичным:
  ```sql
  -- В Supabase SQL Editor
  UPDATE storage.buckets 
  SET public = true 
  WHERE name = 'reels';
  ```

### Ошибка "OpenRouter API key is required"
- Проверьте что добавили `OPENROUTER_API_KEY` в Environment variables
- Или передайте `openrouter_api_key` в input

### Ошибка "Out of memory"
- Увеличьте Memory в Settings (до 4096 MB)
- Или уменьшите `analysis_window_seconds`

### Ошибка "Timeout"
- Увеличьте Timeout в Settings (до 600 секунд)
- Или оптимизируйте код (уменьшите количество анализов)

## Готово! 🎉

Ваш актор готов к работе. Теперь можно:
1. ✅ Запускать анализ через Apify Console
2. ✅ Запускать анализ через Python (`main.py analyze-via-apify`)
3. ✅ Мониторить запуски и стоимость
4. ✅ Оптимизировать под ваши нужды

## Следующие шаги

1. **Настройте Webhook** (опционально):
   - Settings → Webhooks
   - URL: `https://your-api.com/webhook/apify`
   - Event: Run succeeded
   - Payload: Dataset

2. **Настройте Scheduler** (опционально):
   - Schedule → New schedule
   - Cron: `0 */6 * * *` (каждые 6 часов)
   - Input: берите из вашей БД новые рилсы

3. **Масштабируйте**:
   - Запускайте несколько акторов параллельно
   - Используйте Task Queues для большого объёма

