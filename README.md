# Instagram Reel Analyzer Actor

Анализирует Instagram Reels с использованием OpenRouter API:
- **ASR** (Automatic Speech Recognition) - распознавание речи
- **OCR** (Optical Character Recognition) - текст на экране  
- **Visual Events** - визуальные события (лица, текст, логотипы, смены сцен)

## Input

### Обязательные поля:
- `reel_id` - ID рилса в вашей БД
- `video_url` - URL видео для скачивания

### Опциональные поля:
- `caption` - текст caption
- `hashtags` - массив хэштегов
- `analysis_window_seconds` - сколько секунд анализировать (по умолчанию: 5)
- `ocr_times` - моменты времени для OCR (по умолчанию: [0.2, 1.0, 2.0, 3.0, 4.0])
- `openrouter_api_key` - API ключ OpenRouter (или используйте переменную окружения)

### Пример Input:

```json
{
  "reel_id": "e44a1cff-7b06-492a-9975-ea0af6580f28",
  "video_url": "https://xxx.supabase.co/storage/v1/object/public/reels/username/video.mp4",
  "caption": "Kapan sih anak boleh mulai tracing?",
  "hashtags": ["#parenting", "#education"],
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

## Output

Актор сохраняет результаты в dataset:

```json
{
  "reel_id": "e44a1cff-7b06-492a-9975-ea0af6580f28",
  "speech_segments": [
    {"start": 0.0, "end": 2.5, "text": "Kapan sih anak boleh mulai tracing?"}
  ],
  "onscreen_text_segments": [
    {"time": 0.2, "text": "KAPAN SIH ANAK BOLEH MULAI TRACING?"}
  ],
  "visual_events": [
    {"time": 0.2, "event": "FACE_CLOSEUP"},
    {"time": 1.0, "event": "BIG_TEXT"}
  ],
  "metadata": {
    "caption": "Kapan sih anak boleh mulai tracing?",
    "hashtags": ["#parenting", "#education"],
    "analysis_window_seconds": 5,
    "timestamp": "2025-11-18T20:00:00.000Z"
  }
}
```

## Настройка

### 1. Environment Variables

Добавьте в Settings → Environment variables:
- `OPENROUTER_API_KEY` - ваш API ключ OpenRouter

### 2. Build & Run

```bash
# Локально
npm install
npm start

# В Apify Console
# Просто загрузите код и нажмите "Build"
```

## Модели OpenRouter

Актор использует:
- **ASR**: `openai/gpt-4o-audio-preview`
- **OCR**: `anthropic/claude-3.5-sonnet`  
- **Visual Events**: `meta-llama/llama-3.2-90b-vision-instruct`

## Требования

- Node.js >= 18
- ffmpeg (устанавливается автоматически в Docker)
- OpenRouter API key

## Лимиты

- Максимальная длина видео: 30 секунд анализа
- Максимум 5 кадров для OCR (по умолчанию)
- Максимум 3 кадра для Visual Events (ограничение API)

## Стоимость

Примерная стоимость анализа одного рилса через OpenRouter:
- ASR (5 секунд): ~$0.01
- OCR (5 кадров): ~$0.02
- Visual Events (3 кадра): ~$0.03
- **Итого**: ~$0.06 за рилс

## Troubleshooting

### Ошибка "Failed to download video"
- Проверьте, что `video_url` доступен для скачивания
- Если используете Supabase Storage, убедитесь что bucket публичный

### Ошибка "OpenRouter API key is required"
- Добавьте `OPENROUTER_API_KEY` в Environment variables
- Или передайте `openrouter_api_key` в input

### Ошибка "FFmpeg not found"
- При локальном запуске установите ffmpeg: `brew install ffmpeg` (macOS)
- В Apify устанавливается автоматически через Dockerfile

## Интеграция

Результаты автоматически обрабатываются вашим Python кодом:

```bash
python main.py analyze-via-apify --limit 5
```

Код получит результаты из dataset и сохранит в вашу БД.

