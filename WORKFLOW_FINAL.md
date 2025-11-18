# 🎯 Финальный Workflow - Instagram Reels Analysis

## ✅ Что делает система:

```
1. 📥 Apify Актор забирает список роликов из Supabase
2. 📹 Скачивает видео (уже в Supabase Storage)
3. 🧠 Анализирует: ASR + OCR + Visual Events
4. 💾 Сохраняет в Supabase (таблица: reel_analysis_raw)
5. 📄 Генерирует сводку (можно скопировать в Google Docs)
```

---

## 🚀 Полный цикл обработки:

### Шаг 1: Apify Актор (Batch Mode)

**Build актора:**
```
Apify Console → Build → Start Build
```

**Настройте Environment variables:**
```
OPENROUTER_API_KEY = sk-or-v1-...
SUPABASE_URL = https://xxx.supabase.co
SUPABASE_KEY = service-role-key
```

**Запустите с минимальным Input:**
```json
{
  "batch_limit": 10
}
```

Или вообще без input - дефолт `batch_limit: 10`!

**Актор:**
- ✅ Подключится к Supabase
- ✅ Найдёт 10 роликов БЕЗ анализа
- ✅ Обработает каждый (2-3 минуты на ролик)
- ✅ Сохранит в `reel_analysis_raw`
- ✅ Покажет красивую сводку в логах

### Шаг 2: Скопировать сводку в Google Docs

В конце run актора в **Logs** будет:

```
═══════════════════════════════════════════════════════
📊 INSTAGRAM REELS ANALYSIS - BATCH SUMMARY
═══════════════════════════════════════════════════════

📅 Дата анализа: 18.11.2025, 21:00:00
📦 Обработано роликов: 10

───────────────────────────────────────────────────────

1. REEL: e44a1cff-7b06-492a-9975-ea0af6580f28
   URL: https://www.instagram.com/reel/...
   
   📝 РЕЧЬ (ASR):
      [0.0s - 2.5s] Kapan sih anak boleh mulai tracing?
      [2.5s - 5.0s] Yuk simak penjelasan...
      
   🔤 ТЕКСТ НА ЭКРАНЕ (OCR):
      [0.2s] KAPAN SIH ANAK BOLEH MULAI TRACING?
      [1.0s] drg. Hani
      
   👁️  ВИЗУАЛЬНЫЕ СОБЫТИЯ:
      [0.2s] FACE_CLOSEUP
      [1.0s] BIG_TEXT
...
```

**Скопируйте и вставьте в Google Docs!**

Или получите через API:
```bash
curl "https://api.apify.com/v2/key-value-stores/{STORE_ID}/records/BATCH_SUMMARY" \
  -H "Authorization: Bearer YOUR_APIFY_TOKEN"
```

### Шаг 3: Классификация Hooks (Python)

```bash
python main.py classify-hooks
```

Это запустит LLM анализ для классификации хуков:
- Тип хука (QUESTION, PAIN_POINT, BIG_PROMISE, ...)
- Тон (FRIENDLY, SERIOUS, URGENT, ...)
- Язык (id, en, mix)

Результаты → таблица `hooks`

### Шаг 4: Анализ Брендов (Python)

```bash
python main.py analyze-brands
```

Это запустит LLM анализ для обнаружения:
- Упоминания брендов
- Рекламного контента
- Confidence scores

Результаты → таблица `reels` (has_brand_mention, brand_names, is_probable_ad, ...)

### Шаг 5: Обновление Метрик (Python)

```bash
python main.py update-scores
```

Рассчитывает:
- `engagement_rate`
- `hook_score`

Результаты → таблица `reels`

---

## 📊 Итоговые таблицы в Supabase:

### 1. `reels` - Основные данные
```sql
id, url, caption, likes_count, comments_count, 
engagement_rate, hook_score, 
has_brand_mention, brand_names, is_probable_ad
```

### 2. `reel_analysis_raw` - Детальный анализ
```sql
reel_id, speech_text, screen_text, hook_raw_text,
speech_segments, onscreen_text_segments, visual_events,
analysis_context
```

### 3. `hooks` - Классификация хуков
```sql
reel_id, hook_text, hook_type, tone, starts_with, language
```

### 4. `creators` - Данные о создателях
```sql
id, username, full_name, followers
```

---

## 🤖 Автоматизация (Scheduler)

**Apify Console → Schedules:**

- **Cron**: `0 */6 * * *` (каждые 6 часов)
- **Input**: `{"batch_limit": 50}`

Результат: **200 роликов/день автоматически!**

После каждого run:
```bash
# На вашем сервере/локально
python main.py classify-hooks
python main.py analyze-brands  
python main.py update-scores
```

Или настройте webhook для автоматического запуска Python скриптов после Apify run.

---

## 💰 Стоимость

### За 10 роликов:
- Apify актор: ~$0.60 (OpenRouter)
- Python анализ: ~$0.20 (OpenRouter LLM)
- **Итого**: ~$0.80

### Автоматически (200 роликов/день):
- ~$16/день
- ~$480/месяц

---

## 📋 Checklist полной настройки:

- [ ] 1. Apify актор build'нут
- [ ] 2. Environment variables добавлены
- [ ] 3. Тестовый run на 10 роликах успешен
- [ ] 4. Сводка скопирована в Google Docs
- [ ] 5. Python скрипты настроены
- [ ] 6. Scheduler настроен (опционально)
- [ ] 7. Webhook настроен (опционально)

---

## 🎉 Готово!

Теперь у вас полностью автоматизированная система анализа Instagram Reels!

**Вопросы?** Пишите! 🚀

