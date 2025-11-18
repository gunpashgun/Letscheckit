# 🚀 Тестовый Input для Apify актора

## Скопируйте это в Apify Console → Input:

```json
{
  "reel_id": "e44a1cff-7b06-492a-9975-ea0af6580f28",
  "video_url": "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/tumbuhkembanganak.id/DBcEf6fhtSx.mp4",
  "reel_url": "https://www.instagram.com/reel/DBcEf6fhtSx/",
  "shortcode": "DBcEf6fhtSx",
  "caption": "Kapan sih anak boleh mulai tracing? Yuk simak penjelasan drg. Hani ya bun!⁣",
  "hashtags": ["#MilestoneAnak", "#tumbuhkembanganak", "#Parenting", "#smartmoms"],
  "likes_count": 5899,
  "comments_count": 30,
  "video_duration_seconds": 50.433,
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

## Обязательные поля:

- ✅ `reel_id` - ID рилса
- ✅ `video_url` - URL видео для скачивания

## Опциональные поля:

- `caption` - текст caption
- `hashtags` - массив хэштегов
- `analysis_window_seconds` - сколько секунд анализировать (по умолчанию: 5)
- `ocr_times` - моменты времени для OCR (по умолчанию: [0.2, 1.0, 2.0, 3.0, 4.0])

## Минимальный Input (если хотите проще):

```json
{
  "reel_id": "test-123",
  "video_url": "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/tumbuhkembanganak.id/DBcEf6fhtSx.mp4"
}
```

## Ожидаемый результат:

После запуска (15-30 секунд) в **Dataset** появится:

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
    {"time": 0.2, "event": "FACE_CLOSEUP"}
  ]
}
```

## Troubleshooting:

### Ошибка "Input is not valid: Field input.reel_id is required"
→ Вставьте JSON выше (не забудьте `reel_id` и `video_url`)

### Ошибка "Failed to download video"
→ Проверьте что URL доступен:
```bash
curl -I "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/tumbuhkembanganak.id/DBcEf6fhtSx.mp4"
```

### Ошибка "OpenRouter API key is required"
→ Добавьте в Settings → Environment variables:
```
OPENROUTER_API_KEY = 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
```

