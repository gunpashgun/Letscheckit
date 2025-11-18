# 📊 Google Sheets Integration - Setup Guide

## 🎯 Что это даёт

После анализа каждого рилса результаты **автоматически добавляются** в Google Sheets:
- ✅ Timestamp
- ✅ URL рилса
- ✅ ID
- ✅ Caption
- ✅ Текст речи (ASR)
- ✅ Текст на экране (OCR)
- ✅ Визуальные события

**Ваша таблица**: https://docs.google.com/spreadsheets/d/1J0PBI0vTFOhaISOUDo1KbwxqpwlY6Fmq0L_-jw_wIeQ/edit

---

## ⚙️ Настройка (5 минут)

### Шаг 1: Создайте Google Service Account

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. **APIs & Services → Enable APIs**:
   - Включите **Google Sheets API**
4. **APIs & Services → Credentials → Create Credentials → Service Account**:
   - Name: `apify-instagram-analyzer`
   - Role: оставьте пустым (не требуется)
   - Done
5. Кликните на созданный Service Account
6. **Keys → Add Key → Create New Key → JSON**
7. **Скачайте JSON файл**

### Шаг 2: Дайте доступ к таблице

1. Откройте скачанный JSON, найдите `"client_email"`:
   ```json
   "client_email": "apify-instagram-analyzer@project-id.iam.gserviceaccount.com"
   ```

2. Откройте вашу Google Sheets таблицу
3. **Share** (Поделиться)
4. Добавьте этот email с правами **Editor** (Редактор)

### Шаг 3: Добавьте credentials в Apify

**Apify Console → Settings → Environment variables:**

```
GOOGLE_SERVICE_ACCOUNT_JSON = {"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}
```

Скопируйте **ВЕСЬ СОДЕРЖИМОЕ** JSON файла (одной строкой).

---

## 🚀 Использование

### Вариант A: Через Environment Variables (рекомендуется)

Если `GOOGLE_SERVICE_ACCOUNT_JSON` добавлен в Environment variables:

**Input:**
```json
{
  "batch_limit": 10
}
```

Результаты автоматически сохранятся в Google Sheets `1J0PBI0vTFOhaISOUDo1KbwxqpwlY6Fmq0L_-jw_wIeQ`.

### Вариант B: Через Input

Если хотите использовать другую таблицу или другие credentials:

```json
{
  "batch_limit": 10,
  "google_sheets_id": "ДРУГОЙ_ID_ТАБЛИЦЫ",
  "google_service_account_json": "{...JSON...}"
}
```

### Вариант C: Отключить Google Sheets

Удалите `google_sheets_id` из input или Environment variables.

---

## 📋 Структура таблицы

Актор добавляет строки в Sheet1 со следующими колонками:

| A | B | C | D | E | F | G | H | I | J | K |
|---|---|---|---|---|---|---|---|---|---|---|
| Timestamp | URL | ID | Caption | Speech Count | Speech Text | OCR Count | OCR Text | Visual Count | Visual Events | Status |

### Пример строки:

```
18.11.2025, 21:30 | https://instagram.com/reel/... | e44a1cff-... | Kapan sih anak... | 3 | Kapan sih anak boleh... | 5 | KAPAN SIH ANAK... | 2 | 0.2s:FACE_CLOSEUP, 1.0s:BIG_TEXT | Supabase: reel_analysis_raw
```

---

## 📊 Подготовка таблицы

### Рекомендуемая структура Sheet1:

1. Откройте вашу таблицу
2. Добавьте заголовки в первую строку:
   ```
   A1: Дата/время
   B1: URL
   C1: ID
   D1: Caption
   E1: Кол-во речи
   F1: Текст речи
   G1: Кол-во OCR
   H1: Текст OCR
   I1: Кол-во событий
   J1: События
   K1: Статус
   ```

3. Заморозьте первую строку: **View → Freeze → 1 row**

4. (Опционально) Добавьте форматирование:
   - Жирный шрифт для заголовков
   - Цвет фона для заголовков
   - Автоподбор ширины колонок

---

## 🐛 Troubleshooting

### "Google Service Account credentials not found"
→ Проверьте что добавили `GOOGLE_SERVICE_ACCOUNT_JSON` в Environment variables.

### "The caller does not have permission"
→ Убедитесь что Service Account email добавлен в Share вашей таблицы с правами Editor.

### "Unable to parse range"
→ Убедитесь что в таблице есть Sheet1. Или измените `range` в коде на имя вашего листа.

### "Invalid JSON in credentials"
→ JSON должен быть одной строкой без переносов. Или используйте escape для кавычек.

---

## 🔒 Безопасность

**Важно:**
- ✅ Service Account JSON содержит приватный ключ
- ✅ Храните его в Environment variables (не в input!)
- ✅ Не коммитьте в git
- ✅ Давайте доступ только к нужным таблицам

---

## ✅ Готово!

Теперь после каждого Batch run результаты автоматически добавляются в Google Sheets!

**Вопросы?** Спрашивайте! 📊

