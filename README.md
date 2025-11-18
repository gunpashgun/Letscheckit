# Instagram Reel Analyzer Actor

Анализирует Instagram Reels с использованием OpenRouter API:
- **ASR** (Automatic Speech Recognition) - распознавание речи
- **OCR** (Optical Character Recognition) - текст на экране  
- **Visual Events** - визуальные события (лица, текст, логотипы, смены сцен)

## Режимы работы

### 1. Single Reel Mode
Анализ одного рилса напрямую.

### 2. Supabase Batch Mode ⭐ **NEW**
Массовый анализ роликов из Supabase БД.

---

## Input

### Single Reel Mode

```json
{
  "mode": "single",
  "reel_id": "test-123",
  "video_url": "https://example.com/video.mp4",
  "caption": "Test caption",
  "hashtags": ["#test"],
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

**Обязательные поля:**
- `reel_id` - ID рилса
- `video_url` - URL видео

### Supabase Batch Mode

```json
{
  "mode": "supabase_batch",
  "supabase_url": "https://xxx.supabase.co",
  "supabase_key": "service-role-key",
  "batch_limit": 10,
  "filter_unanalyzed_only": true,
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

**Обязательные поля:**
- `supabase_url` - URL Supabase проекта
- `supabase_key` - Service role key

**Опциональные:**
- `batch_limit` - максимум роликов за раз (по умолчанию: 10)
- `filter_unanalyzed_only` - только неанализированные (по умолчанию: true)

---

## Output

### Single Mode
Результаты сохраняются в Apify Dataset:

```json
{
  "reel_id": "test-123",
  "speech_segments": [
    {"start": 0.0, "end": 2.5, "text": "..."}
  ],
  "onscreen_text_segments": [
    {"time": 0.2, "text": "..."}
  ],
  "visual_events": [
    {"time": 0.2, "event": "FACE_CLOSEUP"}
  ],
  "metadata": { ... }
}
```

### Batch Mode
Результаты сохраняются **напрямую в Supabase** в таблицу `reel_analysis_raw`:

```sql
-- Структура записи
{
  reel_id: "...",
  speech_text: "полный текст речи",
  screen_text: "полный текст с экрана",
  hook_raw_text: "speech | screen | caption",
  speech_segments: [...],
  onscreen_text_segments: [...],
  visual_events: [...],
  analysis_context: {...}
}
```

---

## Настройка

### Environment Variables

**Обязательно:**
```
OPENROUTER_API_KEY = sk-or-v1-...
```

**Опционально (для Batch Mode):**
```
SUPABASE_URL = https://xxx.supabase.co
SUPABASE_KEY = service-role-key
```

> Можно передавать Supabase credentials через input или environment variables.

---

## Примеры использования

### 1. Анализ одного рилса

```json
{
  "mode": "single",
  "reel_id": "e44a1cff-7b06-492a-9975-ea0af6580f28",
  "video_url": "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/tumbuhkembanganak.id/DBcEf6fhtSx.mp4",
  "caption": "Kapan sih anak boleh mulai tracing?",
  "hashtags": ["#parenting"]
}
```

### 2. Batch анализ 10 неанализированных роликов

```json
{
  "mode": "supabase_batch",
  "supabase_url": "https://osokxlweresllgbclkme.supabase.co",
  "supabase_key": "eyJhbGci...",
  "batch_limit": 10,
  "filter_unanalyzed_only": true
}
```

### 3. Batch анализ всех роликов (до 100)

```json
{
  "mode": "supabase_batch",
  "supabase_url": "https://osokxlweresllgbclkme.supabase.co",
  "supabase_key": "eyJhbGci...",
  "batch_limit": 100,
  "filter_unanalyzed_only": false
}
```

---

## Модели OpenRouter

- **ASR**: `openai/gpt-4o-audio-preview`
- **OCR**: `anthropic/claude-3.5-sonnet`  
- **Visual Events**: `meta-llama/llama-3.2-90b-vision-instruct`

---

## Стоимость

Примерная стоимость анализа одного рилса:
- ASR (5 секунд): ~$0.01
- OCR (5 кадров): ~$0.02
- Visual Events (3 кадра): ~$0.03
- **Итого**: ~$0.06 за рилс

**Для Batch Mode (100 роликов)**: ~$6

---

## Требования

- Node.js >= 18
- ffmpeg (устанавливается автоматически в Docker)
- OpenRouter API key
- Supabase проект (для Batch Mode)

---

## Troubleshooting

### "Failed to download video"
→ Проверьте URL доступен. Для Supabase убедитесь что bucket `reels` **public**.

### "OpenRouter API key is required"
→ Добавьте `OPENROUTER_API_KEY` в Environment variables.

### "Supabase error: ..."
→ Проверьте `supabase_url` и `supabase_key`. Убедитесь что Service Role Key (не anon key).

### "No reels to process"
→ В Batch Mode: проверьте фильтры. Возможно все ролики уже проанализированы.

---

## Интеграция с Python

После Batch обработки данные доступны в вашей БД:

```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Получить все проанализированные ролики
result = supabase.table('reel_analysis_raw').select('*').execute()

# Запустить классификацию hooks
# python main.py classify-hooks

# Запустить анализ брендов
# python main.py analyze-brands
```

---

## Автоматизация

### Scheduler (рекомендуется)

Настройте Apify Scheduler для автоматической обработки:

1. Apify Console → Schedules → New schedule
2. Cron: `0 */6 * * *` (каждые 6 часов)
3. Input:
```json
{
  "mode": "supabase_batch",
  "batch_limit": 50,
  "filter_unanalyzed_only": true
}
```

### Webhook (опционально)

Отправляйте уведомления после обработки:

1. Settings → Webhooks
2. Event: Run succeeded
3. URL: `https://your-api.com/webhook/apify`

---

## Лицензия

MIT
