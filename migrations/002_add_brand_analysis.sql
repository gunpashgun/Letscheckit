-- Добавляем поле для анализа брендов и рекламы
-- Идеальный дизайн

alter table reel_analysis_raw 
add column if not exists brand_mentions text,
add column if not exists is_advertisement boolean default false,
add column if not exists brand_names text[];

-- Индекс для быстрого поиска рекламных постов
create index if not exists idx_reel_analysis_raw_is_advertisement on reel_analysis_raw(is_advertisement);

