# Примеры использования

## Полный пайплайн обработки

После настройки Supabase и переменных окружения:

```bash
# 1. Импорт данных от Apify
python main.py ingest --json data/apify_reels.json

# 2. Скачивание всех видео
python main.py download-videos

# 3. Анализ текста (ASR + OCR)
python main.py analyze-raw

# 4. Классификация хуков через LLM
python main.py classify-hooks

# 5. Расчёт метрик
python main.py update-scores
```

## Пример JSON от Apify

```json
[
  {
    "id": "3768431061428695271",
    "type": "Video",
    "shortCode": "DRMKBWZAXDn",
    "caption": "It's time to step into an adventure ...",
    "hashtags": ["WonderfulIndonesia"],
    "url": "https://www.instagram.com/p/DRMKBWZAXDn/",
    "videoUrl": "https://scontent-....mp4?stp=...&oe=...&_nc_sid=10d13b",
    "audioUrl": "https://scontent-....mp4?....",
    "likesCount": 1056,
    "commentsCount": 18,
    "videoViewCount": 4551,
    "videoPlayCount": 19565,
    "timestamp": "2025-11-18T07:47:59.000Z",
    "ownerFullName": "Wonderful Indonesia",
    "ownerUsername": "wonderfulindonesia",
    "ownerId": "173601876",
    "productType": "clips",
    "videoDuration": 79.668,
    "inputUrl": "https://www.instagram.com/wonderfulindonesia/reels/"
  }
]
```

## Запросы к БД для анализа

### Топ хуков по hook_score:
```sql
SELECT 
  r.ig_reel_id,
  r.caption,
  h.hook_text,
  h.hook_type,
  h.tone,
  r.hook_score,
  r.engagement_rate
FROM reels r
JOIN hooks h ON r.id = h.reel_id
ORDER BY r.hook_score DESC
LIMIT 10;
```

### Агрегация по типам хуков:
```sql
SELECT 
  h.hook_type,
  COUNT(*) as count,
  AVG(r.hook_score) as avg_score,
  AVG(r.engagement_rate) as avg_er
FROM hooks h
JOIN reels r ON h.reel_id = r.id
GROUP BY h.hook_type
ORDER BY avg_score DESC;
```

### Топ креаторов по среднему hook_score:
```sql
SELECT 
  c.username,
  c.full_name,
  COUNT(r.id) as reel_count,
  AVG(r.hook_score) as avg_hook_score,
  AVG(r.engagement_rate) as avg_er
FROM creators c
JOIN reels r ON c.id = r.creator_id
GROUP BY c.id, c.username, c.full_name
HAVING COUNT(r.id) >= 5
ORDER BY avg_hook_score DESC
LIMIT 20;
```

### Поиск рекламных постов:
```sql
SELECT 
  r.ig_reel_id,
  r.caption,
  a.brand_mentions,
  a.brand_names,
  a.is_advertisement,
  r.hook_score
FROM reels r
JOIN reel_analysis_raw a ON r.id = a.reel_id
WHERE a.is_advertisement = true
ORDER BY r.hook_score DESC;
```

### Анализ брендов:
```sql
SELECT 
  unnest(brand_names) as brand_name,
  COUNT(*) as mention_count,
  AVG(r.hook_score) as avg_hook_score,
  AVG(r.engagement_rate) as avg_er
FROM reel_analysis_raw a
JOIN reels r ON a.reel_id = r.id
WHERE a.brand_names IS NOT NULL AND array_length(a.brand_names, 1) > 0
GROUP BY brand_name
ORDER BY mention_count DESC
LIMIT 20;
```

### Рекламные посты с упоминанием конкретного бренда:
```sql
SELECT 
  r.ig_reel_id,
  r.caption,
  a.brand_names,
  a.brand_mentions,
  r.hook_score
FROM reels r
JOIN reel_analysis_raw a ON r.id = a.reel_id
WHERE 'Nike' = ANY(a.brand_names)  -- замените на нужный бренд
ORDER BY r.hook_score DESC;
```

