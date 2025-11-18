-- Схема БД для Instagram Reels Analysis Pipeline

-- Таблица creators
create table if not exists creators (
  id uuid primary key default gen_random_uuid(),
  ig_owner_id text not null,
  username text not null,
  full_name text,
  followers bigint,           -- можно NULL, если пока нет
  country text,
  niche text,
  created_at timestamptz default now(),
  unique (ig_owner_id)
);

-- Таблица reels
create table if not exists reels (
  id uuid primary key default gen_random_uuid(),
  ig_reel_id text not null,
  shortcode text,
  creator_id uuid references creators(id),
  caption text,
  hashtags text[],
  url text,                   -- ссылка на пост в инсте
  posted_at timestamptz,
  
  -- метрики
  likes_count int,
  comments_count int,
  video_view_count int,       -- уникальные
  video_play_count int,       -- сколько раз воспроизвели

  video_duration_seconds numeric,
  
  -- ссылки на медиа
  source_video_url text,      -- исходный CDN от Apify
  storage_video_path text,    -- путь в Supabase Storage (bucket/key)
  storage_thumb_path text,    -- опционально

  raw_json jsonb,             -- весь объект из Apify для отладки

  -- метрики и скоринг
  engagement_rate numeric,
  hook_score numeric,

  created_at timestamptz default now(),

  unique (ig_reel_id)
);

-- Таблица reel_analysis_raw
create table if not exists reel_analysis_raw (
  id uuid primary key default gen_random_uuid(),
  reel_id uuid references reels(id),
  speech_text text,           -- транскрипт первых N секунд
  screen_text text,           -- текст с экрана (OCR)
  caption_hook_text text,     -- первые строки caption
  hook_raw_text text,         -- конкатенация всего
  created_at timestamptz default now(),
  unique (reel_id)
);

-- Таблица hooks
create table if not exists hooks (
  id uuid primary key default gen_random_uuid(),
  reel_id uuid references reels(id),
  hook_text text,             -- нормализованный короткий хук
  hook_type text,             -- QUESTION / PAIN_POINT / BIG_PROMISE / ...
  tone text,                  -- FRIENDLY / SERIOUS / URGENT / FUNNY / ...
  starts_with text,           -- QUESTION / NUMBER / STATEMENT / VISUAL_ONLY
  language text,              -- id / en / mix
  model_name text,
  created_at timestamptz default now()
);

-- Индексы для производительности
create index if not exists idx_reels_creator_id on reels(creator_id);
create index if not exists idx_reels_posted_at on reels(posted_at);
create index if not exists idx_reels_hook_score on reels(hook_score);
create index if not exists idx_reel_analysis_raw_reel_id on reel_analysis_raw(reel_id);
create index if not exists idx_hooks_reel_id on hooks(reel_id);
create index if not exists idx_hooks_hook_type on hooks(hook_type);

