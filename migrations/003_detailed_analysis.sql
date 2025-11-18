-- Детальный анализ с таймкодами и визуальными событиями
-- Идеальный дизайн

-- Обновляем таблицу hooks для поддержки нескольких хуков на рилс с таймкодами
alter table hooks 
add column if not exists time_start numeric,
add column if not exists time_end numeric,
add column if not exists channel text,  -- VOICE | TEXT | VISUAL | MIX
add column if not exists strength int;   -- 1-10

-- Добавляем поля брендов/рекламы в таблицу reels
alter table reels
add column if not exists has_brand_mention boolean default false,
add column if not exists brand_names text[],
add column if not exists brand_sources text[],  -- SPEECH, ONSCREEN_TEXT, MENTION_OR_TAG, CAPTION, VISUAL_LOGO
add column if not exists is_probable_ad boolean default false,
add column if not exists ad_type text,  -- BRAND_POST | SPONSORSHIP | UGC_LIKE_AD | ORGANIC_CONTENT
add column if not exists ad_description text,
add column if not exists brand_confidence numeric,  -- 0.0-1.0
add column if not exists ad_confidence numeric;    -- 0.0-1.0

-- Обновляем reel_analysis_raw для хранения детальных сегментов
alter table reel_analysis_raw
add column if not exists speech_segments jsonb,      -- массив {start, end, text}
add column if not exists onscreen_text_segments jsonb, -- массив {time, text}
add column if not exists visual_events jsonb,         -- массив {time, event}
add column if not exists analysis_context jsonb;     -- полный JSON контекст для LLM

-- Индексы
create index if not exists idx_hooks_time_start on hooks(time_start);
create index if not exists idx_reels_is_probable_ad on reels(is_probable_ad);
create index if not exists idx_reels_has_brand_mention on reels(has_brand_mention);

