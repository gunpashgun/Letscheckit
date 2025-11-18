-- Безопасная миграция: создаёт таблицы только если их нет
-- Не изменяет существующие таблицы и не удаляет данные

-- Таблица creators
create table if not exists creators (
  id uuid primary key default gen_random_uuid(),
  ig_owner_id text not null,
  username text not null,
  full_name text,
  followers bigint,
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
  url text,
  posted_at timestamptz,
  likes_count int,
  comments_count int,
  video_view_count int,
  video_play_count int,
  video_duration_seconds numeric,
  source_video_url text,
  storage_video_path text,
  storage_thumb_path text,
  raw_json jsonb,
  engagement_rate numeric,
  hook_score numeric,
  created_at timestamptz default now(),
  unique (ig_reel_id)
);

-- Таблица reel_analysis_raw
create table if not exists reel_analysis_raw (
  id uuid primary key default gen_random_uuid(),
  reel_id uuid references reels(id),
  speech_text text,
  screen_text text,
  caption_hook_text text,
  hook_raw_text text,
  created_at timestamptz default now(),
  unique (reel_id)
);

-- Таблица hooks
create table if not exists hooks (
  id uuid primary key default gen_random_uuid(),
  reel_id uuid references reels(id),
  hook_text text,
  hook_type text,
  tone text,
  starts_with text,
  language text,
  model_name text,
  created_at timestamptz default now()
);

-- Индексы (создаются только если их нет)
create index if not exists idx_reels_creator_id on reels(creator_id);
create index if not exists idx_reels_posted_at on reels(posted_at);
create index if not exists idx_reels_hook_score on reels(hook_score);
create index if not exists idx_reel_analysis_raw_reel_id on reel_analysis_raw(reel_id);
create index if not exists idx_hooks_reel_id on hooks(reel_id);
create index if not exists idx_hooks_hook_type on hooks(hook_type);

-- Добавляем недостающие колонки, если таблицы уже существуют
-- (эти команды безопасны - они ничего не сделают, если колонки уже есть)

-- Для таблицы reels
do $$
begin
  if exists (select 1 from information_schema.tables where table_name = 'reels') then
    -- Добавляем колонки, если их нет
    if not exists (select 1 from information_schema.columns where table_name = 'reels' and column_name = 'engagement_rate') then
      alter table reels add column engagement_rate numeric;
    end if;
    if not exists (select 1 from information_schema.columns where table_name = 'reels' and column_name = 'hook_score') then
      alter table reels add column hook_score numeric;
    end if;
  end if;
end $$;

