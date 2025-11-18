# Instagram Reels Analysis Pipeline

Сервис для обработки Instagram-рилсов из Apify JSON: скачивание видео, анализ текста (ASR + OCR), классификация хуков через LLM и расчёт метрик.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Установите системные зависимости:
- **ffmpeg**: для обработки видео/аудио
- **tesseract**: для OCR (с поддержкой indonesian и english языков)

На macOS:
```bash
brew install ffmpeg tesseract tesseract-lang
```

На Ubuntu/Debian:
```bash
sudo apt-get install ffmpeg tesseract-ocr tesseract-ocr-ind
```

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
    analyzer_audio.py      # Вырезка аудио, Whisper транскрипция
    analyzer_ocr.py        # Извлечение кадров + OCR
    analyzer_raw.py        # Комбинированный анализ (ASR + OCR + caption)
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
- ASR использует faster-whisper (модель `medium`) с приоритетом для indonesian языка
- OCR извлекает 2-4 кадра из первых 2-3 секунд видео
- LLM классификация использует OpenRouter API (модель настраивается в `services/analyzer_hooks.py`)

