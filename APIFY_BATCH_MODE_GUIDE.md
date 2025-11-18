# 🚀 Apify Batch Mode - Массовая обработка из Supabase

## ✅ Что сделано

Апдейтнул актор - теперь он умеет **забирать ролики напрямую из Supabase** и обрабатывать их пачками!

### Два режима работы:

1. **Single Mode** - анализ одного рилса (как раньше)
2. **Supabase Batch Mode** ⭐ **NEW** - массовый анализ из БД

---

## 🎯 Как использовать Batch Mode

### 1. Build актора заново

```
Apify Console → Build → Start Build
```

Новый код уже запушен в ветку `apify-actor-clean`.

### 2. Добавьте Supabase credentials

**Вариант A: через Environment Variables (безопаснее)**

Apify Console → Settings → Environment variables:
```
OPENROUTER_API_KEY = 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
SUPABASE_URL = https://osokxlweresllgbclkme.supabase.co
SUPABASE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Вариант B: через Input (для тестирования)**

Можно передавать в input напрямую (см. примеры ниже).

### 3. Запустите Batch обработку

В Apify Console → Input вставьте:

```json
{
  "mode": "supabase_batch",
  "supabase_url": "https://osokxlweresllgbclkme.supabase.co",
  "supabase_key": "YOUR_SERVICE_ROLE_KEY",
  "batch_limit": 10,
  "filter_unanalyzed_only": true,
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

Нажмите **Start** → актор:
1. Подключится к Supabase
2. Получит список роликов (до 10 штук)
3. Обработает каждый (ASR + OCR + Visual Events)
4. **Сохранит результаты напрямую в Supabase** в таблицу `reel_analysis_raw`

---

## 📊 Что он делает

### Алгоритм Batch Mode:

```
1. Подключается к Supabase
2. Получает список reels:
   - С заполненным storage_video_path (видео скачано)
   - Без записи в reel_analysis_raw (ещё не анализировали)
   - Limit: batch_limit (по умолчанию 10)
3. Для каждого reel:
   - Формирует video_url из storage_video_path
   - Скачивает видео
   - Делает ASR, OCR, Visual Events
   - Сохраняет результаты в reel_analysis_raw
4. Логирует прогресс: [1/10], [2/10], ...
```

### Что сохраняется в БД:

```sql
-- Таблица: reel_analysis_raw
{
  reel_id: "uuid",
  speech_text: "полный текст речи",
  screen_text: "полный текст с экрана",
  caption_hook_text: "первая строка caption",
  hook_raw_text: "speech | screen | caption",
  speech_segments: [{"start": 0.0, "end": 2.5, "text": "..."}],
  onscreen_text_segments: [{"time": 0.2, "text": "..."}],
  visual_events: [{"time": 0.2, "event": "FACE_CLOSEUP"}],
  analysis_context: { ... полный контекст для LLM ... }
}
```

---

## 💡 Примеры использования

### Пример 1: Обработать 10 новых роликов

```json
{
  "mode": "supabase_batch",
  "batch_limit": 10,
  "filter_unanalyzed_only": true
}
```

*(требует Environment variables: SUPABASE_URL, SUPABASE_KEY)*

### Пример 2: Обработать 50 роликов (любых)

```json
{
  "mode": "supabase_batch",
  "supabase_url": "https://osokxlweresllgbclkme.supabase.co",
  "supabase_key": "eyJhbGci...",
  "batch_limit": 50,
  "filter_unanalyzed_only": false
}
```

### Пример 3: Single Mode (как раньше)

```json
{
  "mode": "single",
  "reel_id": "test-123",
  "video_url": "https://example.com/video.mp4"
}
```

---

## 🔄 Workflow после Batch обработки

После того как актор обработал ролики:

### 1. Проверьте результаты в БД

```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Получить все проанализированные ролики
result = supabase.table('reel_analysis_raw').select('*').execute()
print(f"Проанализировано роликов: {len(result.data)}")
```

### 2. Запустите классификацию hooks

```bash
python main.py classify-hooks
```

Это запустит LLM анализ для хуков на основе `hook_raw_text`.

### 3. Запустите анализ брендов

```bash
python main.py analyze-brands
```

Это запустит LLM анализ для обнаружения брендов/рекламы.

### 4. Обновите метрики

```bash
python main.py update-scores
```

---

## 📅 Автоматизация (Scheduler)

Настройте автоматический запуск каждые 6 часов:

### 1. Apify Console → Schedules → New schedule

- **Name**: Instagram Reels Batch Analysis
- **Cron**: `0 */6 * * *` (каждые 6 часов)
- **Actor**: Ваш актор
- **Input**:
```json
{
  "mode": "supabase_batch",
  "batch_limit": 50,
  "filter_unanalyzed_only": true
}
```

### 2. Webhook для уведомлений (опционально)

Settings → Webhooks:
- Event: Run succeeded
- URL: `https://your-api.com/webhook/apify`
- Payload: Dataset

---

## 💰 Стоимость

### Batch Mode (10 роликов):
- 10 роликов × $0.06 = **$0.60**
- Время: ~5-10 минут

### Batch Mode (100 роликов):
- 100 роликов × $0.06 = **$6**
- Время: ~30-60 минут

### Scheduler (автоматически каждые 6 часов):
- 4 запуска в день × 50 роликов = 200 роликов/день
- **~$12/день** или **~$360/месяц**

---

## ⚠️ Важные моменты

### 1. Service Role Key
Используйте **Service Role Key**, а не anon key!

Получить в Supabase Dashboard:
```
Settings → API → service_role (secret)
```

### 2. Public bucket
Убедитесь что Supabase bucket `reels` **public**:

```sql
-- В Supabase SQL Editor
UPDATE storage.buckets 
SET public = true 
WHERE name = 'reels';
```

Или в Storage → reels → Settings → Make public

### 3. Лимиты
- Максимальный `batch_limit`: **100 роликов**
- Рекомендуемый: **10-50 роликов** за раз

---

## 🐛 Troubleshooting

### "Supabase error: ..."
→ Проверьте credentials. Используйте Service Role Key.

### "No reels to process"
→ Все ролики уже проанализированы. Попробуйте `filter_unanalyzed_only: false`.

### "Failed to download video"
→ Проверьте что bucket `reels` публичный.

### "Out of memory"
→ Уменьшите `batch_limit` (попробуйте 10 вместо 50).

---

## 🎉 Готово!

Теперь можно обрабатывать сотни роликов автоматически!

### Следующие шаги:

1. **Build актора** (новый код уже в `apify-actor-clean`)
2. **Добавьте credentials** в Environment variables
3. **Запустите Batch** с `batch_limit: 10` для теста
4. **Настройте Scheduler** для автоматизации
5. **Проверьте результаты** в Supabase

Вопросы? Спрашивайте! 🚀

