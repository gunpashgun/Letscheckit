# Instagram Reels Analysis Pipeline

Сервис для обработки Instagram-рилсов из Apify: скачивание видео, анализ текста и хуков, расчёт метрик.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Скопируйте `.env.example` в `.env` и заполните переменные окружения:
```bash
cp .env.example .env
```

3. Убедитесь, что установлены системные зависимости:
- FFmpeg (для обработки видео/аудио)
  ```bash
  # macOS
  brew install ffmpeg
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  ```
- Tesseract OCR (для распознавания текста)
  ```bash
  # macOS
  brew install tesseract tesseract-lang
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr tesseract-ocr-ind
  ```

## Использование

### Инициализация базы данных

1. Выполните SQL-скрипт из `migrations/001_initial_schema.sql` в Supabase SQL Editor.

2. Создайте Storage bucket для видео:
   - Откройте Supabase Dashboard → Storage
   - Создайте новый bucket с именем `reels`
   - Установите как приватный (public: false)
   - Настройте политики доступа по необходимости

### Запуск пайплайна

```bash
# 1. Импорт JSON от Apify
python main.py ingest --json path/to/apify_data.json

# 2. Скачивание видео
python main.py download-videos

# 3. Извлечение текста (ASR + OCR)
python main.py analyze-raw

# 4. Классификация хуков через LLM
python main.py classify-hooks

# 5. Расчёт метрик и скоринг
python main.py update-scores
```

## Структура проекта

- `models/` - Pydantic модели для данных
  - `apify_reel.py` - модель для JSON от Apify
- `services/` - Бизнес-логика сервисов
  - `supabase_client.py` - инициализация Supabase клиента
  - `ingestion.py` - импорт JSON, создание creators/reels
  - `downloader.py` - скачивание видео и загрузка в Storage
  - `analyzer.py` - основной анализатор (ASR + OCR + caption)
  - `analyzer_audio.py` - Whisper ASR
  - `analyzer_ocr.py` - OCR извлечение текста
  - `analyzer_hooks.py` - классификация хуков через OpenRouter
  - `scoring.py` - расчёт engagement_rate и hook_score
- `main.py` - CLI точка входа
- `migrations/` - SQL миграции для базы данных

## Переменные окружения

Создайте файл `.env` со следующими переменными:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Пример использования

```bash
# Импорт данных
python main.py ingest --json example_apify_data.json

# Обработка всех этапов последовательно
python main.py download-videos
python main.py analyze-raw
python main.py classify-hooks
python main.py update-scores

# Параллельная обработка (быстрее для больших объёмов)
python main.py download-videos --parallel --workers 8
python main.py analyze-raw --parallel --workers 4
python main.py classify-hooks --parallel --workers 6
```

## Параллельная обработка

Проект поддерживает параллельную обработку для ускорения работы:

- **`--parallel`** — включает параллельную обработку
- **`--workers N`** — количество параллельных воркеров (по умолчанию: 4 для download/classify, 2 для analysis)

**Рекомендации:**
- `download-videos`: используйте threads (I/O-bound), 4-8 воркеров
- `analyze-raw`: используйте processes (CPU-bound), 2-4 воркера (зависит от CPU)
- `classify-hooks`: используйте threads (I/O-bound, ожидание API), 4-8 воркеров

**Пример:**
```bash
# Скачать 100 видео параллельно (8 потоков)
python main.py download-videos --parallel --workers 8

# Анализировать видео параллельно (4 процесса)
python main.py analyze-raw --parallel --workers 4
```

## Примечания

- Видео скачиваются напрямую с CDN URL от Apify (без обрезки)
- Whisper использует модель `medium` (можно изменить в `analyzer_audio.py`)
- OpenRouter использует модель `openrouter/auto` (можно изменить в `analyzer_hooks.py`)
- Все операции имеют встроенные retry механизмы для сетевых ошибок
- Параллельная обработка автоматически создаёт Supabase клиент в каждом воркере

