-- Добавление полей для детального анализа в reel_analysis_raw

-- Добавляем поля для хранения структурированных данных анализа
alter table reel_analysis_raw 
  add column if not exists speech_segments jsonb,
  add column if not exists onscreen_text_segments jsonb,
  add column if not exists visual_events jsonb,
  add column if not exists analysis_context jsonb;

-- Комментарии к полям
comment on column reel_analysis_raw.speech_segments is 'ASR сегменты с таймкодами: [{"text": "...", "start": 0.0, "end": 2.5}, ...]';
comment on column reel_analysis_raw.onscreen_text_segments is 'OCR сегменты с таймкодами: [{"text": "...", "timestamp": 1.0}, ...]';
comment on column reel_analysis_raw.visual_events is 'Визуальные события: [{"type": "text_appears", "timestamp": 1.0}, ...]';
comment on column reel_analysis_raw.analysis_context is 'Полный JSON контекст для LLM анализа';

