# 🚀 Quick Start - 5 минут до запуска

## 1️⃣ Загрузите код в Apify (2 минуты)

### Вариант A: GitHub (рекомендуется)
```bash
cd apify_actor/
git init
git add .
git commit -m "Apify actor"
git push
```
В Apify Console:
- Source: **GitHub** → укажите репозиторий

### Вариант B: Web IDE
Скопируйте все файлы в Apify Console → Source → Web IDE

---

## 2️⃣ Добавьте API ключ (30 секунд)

```
Apify Console → Settings → Environment variables
```

Добавьте:
```
OPENROUTER_API_KEY = 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
```

---

## 3️⃣ Build актора (3 минуты)

```
Apify Console → Build → Start Build
```
☕ Ждём завершения...

---

## 4️⃣ Тестовый запуск (30 секунд)

В **Input** вставьте:
```json
{
  "reel_id": "test-123",
  "video_url": "https://osokxlweresllgbclkme.supabase.co/storage/v1/object/public/reels/tumbuhkembanganak.id/DBcEf6fhtSx.mp4",
  "caption": "Test",
  "hashtags": [],
  "analysis_window_seconds": 5,
  "ocr_times": [0.2, 1.0, 2.0, 3.0, 4.0]
}
```

Нажмите **Start** → проверьте логи и Dataset.

---

## 5️⃣ Интеграция с Python (1 минута)

Добавьте в `.env`:
```bash
APIFY_API_TOKEN=apify_api_xxxxxxxxx  # Из Apify Settings → Integrations
APIFY_ACTOR_ID=DRPr1b1S4f7LehPKg
```

Запустите:
```bash
python main.py analyze-via-apify --limit 1
```

---

## ✅ Готово!

Проверьте результаты:
```bash
python3 -c "
from services.supabase_client import get_supabase_client
result = get_supabase_client().table('reel_analysis_raw').select('*').limit(1).execute()
print(result.data)
"
```

---

## 📊 Что дальше?

### Массовый анализ
```bash
python main.py analyze-via-apify --workers 10
```

### Мониторинг
- Apify Console → Runs (проверяйте статус и стоимость)
- Dataset (проверяйте результаты)

### Оптимизация
- Уменьшите `analysis_window_seconds` (3 вместо 5)
- Уменьшите `ocr_times` (3 кадра вместо 5)
- Используйте более дешёвые модели

---

## 🐛 Проблемы?

### Build failed
→ Проверьте все файлы загружены

### Download failed
→ Убедитесь что Supabase bucket `reels` **public**

### API error
→ Проверьте `OPENROUTER_API_KEY` в Environment variables

### Timeout
→ Увеличьте Timeout в Settings (до 600s)

---

## 💰 Стоимость

~$0.06 за рилс
~$60 за 1000 рилсов

---

**Подробная инструкция:** `DEPLOY_GUIDE.md`
**Вопросы?** Просто спросите! 🚀

