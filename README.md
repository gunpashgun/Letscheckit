# Instagram Reels Analysis Pipeline

Сервис для обработки Instagram-рилсов из Apify JSON: скачивание видео, анализ текста (ASR + OCR), классификация хуков через LLM и расчёт метрик.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Установите системные зависимости:
- **opencv-python**: для извлечения кадров из видео (устанавливается через pip)

Примечание: Анализ видео и текста выполняется через OpenRouter vision модели, локальные инструменты (Whisper, Tesseract) не требуются.

3. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

Заполните переменные:
- `SUPABASE_URL` - URL вашего Supabase проекта
- `SUPABASE_SERVICE_ROLE_KEY` - Service Role Key из Supabase
- `OPENROUTER_API_KEY` - API ключ OpenRouter

## Настройка Supabase

1. **Создание таблиц**: Выполните SQL-скрипт из `migrations/001_initial_schema.sql` в SQL Editor вашего Supabase проекта.

2. **Создание Storage bucket**: 
   - Перейдите в Storage → Create a new bucket
   - Название: `reels`
   - Public bucket: можно сделать публичным или приватным (в зависимости от ваших нужд)
   - File size limit: установите подходящий лимит (например, 100MB)

3. **Проверка переменных окружения**: Убедитесь, что `.env` файл содержит правильные значения для `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY`.

## Использование

### 1. Импорт JSON от Apify
```bash
python main.py ingest --json path/to/apify_data.json
```

### 2. Скачивание видео
```bash
python main.py download-videos
```

### 3. Анализ текста (ASR + OCR)
```bash
python main.py analyze-raw
```

### 4. Классификация хуков через LLM
```bash
python main.py classify-hooks
```

### 5. Обновление метрик
```bash
python main.py update-scores
```

## Структура проекта

```
project/
  main.py                  # CLI точка входа
  models/
    apify_reel.py          # Pydantic модели для Apify JSON
  services/
    supabase_client.py     # Инициализация Supabase клиента
    ingestion.py           # Парсинг JSON, создание creators/reels
    downloader.py          # Скачивание видео и загрузка в Storage
    analyzer_openrouter.py # Анализ видео кадров через OpenRouter vision модели
    analyzer_raw.py        # Комбинированный анализ (видео + caption)
    analyzer_hooks.py      # OpenRouter LLM классификация хуков
    scoring.py             # Расчёт engagement_rate и hook_score
```

## Схема БД

См. описание таблиц в документации:
- `creators` - информация о креаторах
- `reels` - метаданные рилсов
- `reel_analysis_raw` - сырой анализ текста
- `hooks` - классифицированные хуки

## Примечания

- Видео скачиваются стримом с ретраями при сетевых ошибках
- Анализ видео выполняется через OpenRouter vision модели (идеальный дизайн):
  - Извлекаются кадры из первых 5 секунд видео целиком (10 кадров через opencv)
  - Кадры анализируются vision моделью (по умолчанию `google/gemini-2.0-flash-exp:free`)
  - Модель извлекает текст с экрана (OCR), речь (если есть субтитры) и определяет бренды/рекламу
  - Определяются упоминания брендов, намёки на бренды, рекламный контент
- LLM классификация хуков использует OpenRouter API (модель настраивается в `services/analyzer_hooks.py`)
- Vision модель для анализа видео настраивается в `services/analyzer_openrouter.py`
- Данные о брендах сохраняются в `reel_analysis_raw`: `brand_mentions`, `is_advertisement`, `brand_names`

