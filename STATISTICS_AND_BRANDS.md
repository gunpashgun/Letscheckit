# 📊 Статистика и Анализ Брендов

## ✅ Что добавлено

### 1. Статистика из JSON в Google Sheets

Теперь сохраняются:
- ✅ **Лайки** (`likes_count`)
- ✅ **Комментарии** (`comments_count`)
- ✅ **Просмотры** (`video_view_count` или `video_play_count`)

### 2. Анализ Брендов

Автоматически определяется:
- ✅ **Названия брендов** (если упоминаются в видео)
- ✅ **Была реклама** (True/False) - параметр `is_probable_ad`

---

## 📊 Новая структура Google Sheets

| Колонка | Описание | Пример |
|---------|----------|--------|
| A | Дата/время анализа | 18.11.2025, 21:30 |
| B | URL рилса | https://instagram.com/reel/... |
| C | ID | e44a1cff-... |
| D | Caption | Kapan sih anak... |
| **E** | **Лайки** | **5899** |
| **F** | **Комментарии** | **30** |
| **G** | **Просмотры** | **125000** |
| H | Кол-во речевых сегментов | 3 |
| I | Текст речи | Kapan sih anak boleh... |
| J | Кол-во OCR | 5 |
| K | Текст OCR | KAPAN SIH ANAK... |
| L | Кол-во визуальных событий | 2 |
| M | Визуальные события | 0.2s:FACE_CLOSEUP... |
| **N** | **Обнаруженные бренды** | **Nutrimate, drg. Hani** |
| **O** | **Была реклама** | **True** |
| P | Статус | Supabase: reel_analysis_raw |

---

## 🧠 Как работает анализ брендов

### Этап 1: Apify Актор (Video Analysis)
```
1. Анализирует видео (ASR, OCR, Visual Events)
2. Сохраняет в Supabase
3. Добавляет строку в Google Sheets
   - Статистика: лайки, комменты, просмотры ✅
   - Бренды: "Pending Python analysis" (пока)
   - Реклама: "Pending Python analysis" (пока)
```

### Этап 2: Python Анализ Брендов
```bash
python main.py analyze-brands
```

Что делает:
1. Берёт `analysis_context` из `reel_analysis_raw`
2. Отправляет в LLM (Claude 3.5 Sonnet через OpenRouter)
3. LLM анализирует:
   - Речь (ASR)
   - Текст на экране (OCR)
   - Визуальные события
   - Caption и hashtags
4. Определяет:
   - `has_brand_mention`: True/False
   - `brand_names`: ["Nutrimate", "drg. Hani"]
   - `brand_sources`: ["SPEECH", "CAPTION", "VISUAL_LOGO"]
   - `is_probable_ad`: True/False
   - `ad_type`: "BRAND_POST" | "SPONSORSHIP" | "UGC_LIKE_AD" | "ORGANIC_CONTENT"
   - `ad_description`: "Реклама приложения Nutrimate для MPASI"
   - `brand_confidence`: 0.95 (0-1)
   - `ad_confidence`: 0.85 (0-1)
5. Сохраняет в таблицу `reels`

---

## 🔍 Пример анализа бренда

### Input (analysis_context):
```json
{
  "speech_segments": [
    {"text": "Download Nutrimate sekarang"}
  ],
  "onscreen_text_segments": [
    {"text": "NUTRIMATE - MPASI APP"}
  ],
  "visual_events": [
    {"event": "LOGO_OR_BRAND_OBJECT"}
  ],
  "caption": "Bikin jadwal makan sehat dengan Nutrimate!",
  "hashtags": ["#Nutrimate"]
}
```

### Output:
```json
{
  "has_brand_mention": true,
  "brand_names": ["Nutrimate"],
  "brand_sources": ["SPEECH", "ONSCREEN_TEXT", "CAPTION", "VISUAL_LOGO"],
  "is_probable_ad": true,
  "ad_type": "BRAND_POST",
  "ad_description": "Прямая реклама мобильного приложения Nutrimate для планирования питания детей (MPASI)",
  "brand_confidence": 0.95,
  "ad_confidence": 0.90
}
```

---

## 📋 Полный Workflow

### 1. Apify Актор (автоматически каждые 6 часов)
```json
Input: {"batch_limit": 50}
```

**Результат:**
- ✅ 50 роликов проанализированы
- ✅ Сохранены в Supabase (reel_analysis_raw)
- ✅ Добавлены в Google Sheets (со статистикой)
- ⏳ Бренды: "Pending Python analysis"

### 2. Python: Анализ Брендов
```bash
python main.py analyze-brands
```

**Результат:**
- ✅ LLM проанализировал каждый ролик
- ✅ Определены бренды и реклама
- ✅ Сохранено в таблицу `reels`

### 3. (Опционально) Обновить Google Sheets
Можно создать скрипт для обновления колонок N и O:

```python
# update_sheets_with_brands.py
from supabase import create_client
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Получить все ролики с брендами
reels = supabase.table('reels').select('id, brand_names, is_probable_ad').execute()

# Обновить Google Sheets
for reel in reels.data:
    brands = ', '.join(reel['brand_names']) if reel['brand_names'] else 'None'
    is_ad = 'True' if reel['is_probable_ad'] else 'False'
    
    # Найти строку по ID и обновить колонки N и O
    # ...
```

---

## 🎯 База Данных

### Таблица `reels` - Хранит всё:

```sql
CREATE TABLE reels (
  id UUID PRIMARY KEY,
  url TEXT,
  caption TEXT,
  likes_count INTEGER,           -- ✅ Статистика
  comments_count INTEGER,        -- ✅ Статистика
  video_view_count INTEGER,      -- ✅ Статистика
  has_brand_mention BOOLEAN,     -- ✅ Анализ брендов
  brand_names TEXT[],            -- ✅ Названия брендов
  brand_sources TEXT[],          -- Откуда обнаружены
  is_probable_ad BOOLEAN,        -- ✅ Была реклама (True/False)
  ad_type TEXT,                  -- Тип рекламы
  ad_description TEXT,           -- Описание
  brand_confidence NUMERIC,      -- Уверенность (0-1)
  ad_confidence NUMERIC          -- Уверенность (0-1)
);
```

---

## 📊 Примеры Запросов

### Найти все рекламные ролики:
```sql
SELECT id, url, brand_names, ad_type, likes_count, comments_count
FROM reels
WHERE is_probable_ad = true
ORDER BY likes_count DESC;
```

### Топ брендов по количеству роликов:
```sql
SELECT 
  unnest(brand_names) as brand,
  COUNT(*) as reel_count,
  AVG(likes_count) as avg_likes
FROM reels
WHERE has_brand_mention = true
GROUP BY brand
ORDER BY reel_count DESC;
```

### Эффективность рекламных vs органических:
```sql
SELECT 
  is_probable_ad,
  AVG(likes_count) as avg_likes,
  AVG(comments_count) as avg_comments,
  AVG(video_view_count) as avg_views
FROM reels
GROUP BY is_probable_ad;
```

---

## ✅ Готово!

Теперь система:
1. ✅ Сохраняет статистику (лайки, комменты, просмотры)
2. ✅ Анализирует бренды через LLM
3. ✅ Определяет рекламный контент
4. ✅ Всё добавляется в Google Sheets и БД

**Вопросы?** Спрашивайте! 📊🚀

