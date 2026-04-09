create extension if not exists pgcrypto;
create extension if not exists vector;


create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;


create table if not exists restaurants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    chain_brand text,
    address text not null,
    city text,
    state text,
    postal_code text,
    country text default 'US',

    lat double precision,
    lng double precision,
    cuisine text,

    website_url text,
    menu_url text,
    phone text,

    deep_status text default 'not_started', 
    discovery_confidence real default 0.0,

    last_discovered_at timestamptz,
    last_deep_refresh_at timestamptz,
    next_refresh_at timestamptz,

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create trigger trg_restaurants_updated_at
before update on restaurants
for each row execute function set_updated_at();


create table if not exists discovery_runs (
    id uuid primary key default gen_random_uuid(),
    center_lat double precision not null,
    center_lng double precision not null,
    radius_miles real not null,
    category text,
    status text default 'running', 
    started_at timestamptz default now(),
    completed_at timestamptz
);


create table if not exists discovery_run_restaurants (
    discovery_run_id uuid not null references discovery_runs(id) on delete cascade,
    restaurant_id uuid not null references restaurants(id) on delete cascade,
    discovered_rank integer,
    source_url text,
    primary key (discovery_run_id, restaurant_id)
);

create table if not exists restaurant_pages (
    id uuid primary key default gen_random_uuid(),
    restaurant_id uuid not null references restaurants(id) on delete cascade,
    page_type text not null, 
    url text not null,
    content_hash text,
    fetch_status text default 'success',
    last_fetched_at timestamptz default now()
);


create unique index if not exists uq_restaurant_pages_restaurant_url
on restaurant_pages (restaurant_id, url);

create table if not exists menu_items (
    id uuid primary key default gen_random_uuid(),
    restaurant_id uuid not null references restaurants(id) on delete cascade,
    name text not null,
    category text,
    description text,
    price numeric(10,2),

    evidence_source_type text default 'restaurant_explicit', -- restaurant_explicit | restaurant_inferred | generic_recipe
    extraction_confidence real default 0.0,

    last_seen_at timestamptz default now(),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create trigger trg_menu_items_updated_at
before update on menu_items
for each row execute function set_updated_at();


create table if not exists menu_item_facts (
    menu_item_id uuid primary key references menu_items(id) on delete cascade,

    ingredients_explicit jsonb default '[]'::jsonb,
    ingredients_inferred jsonb default '[]'::jsonb,
    allergens_explicit jsonb default '[]'::jsonb,
    preparation_tags jsonb default '[]'::jsonb,
    uncertainty_flags jsonb default '[]'::jsonb,
    nutrition_explicit jsonb default '{}'::jsonb,

    last_extracted_at timestamptz default now()
);


create table if not exists condition_evaluations (
    id uuid primary key default gen_random_uuid(),
    menu_item_id uuid not null references menu_items(id) on delete cascade,
    condition_id text not null,

    label text not null, -- Compatible | Caution | High risk | Unclear
    score real not null,
    confidence real not null,

    reasons jsonb default '[]'::jsonb,
    missing_info jsonb default '[]'::jsonb,
    matched_rules jsonb default '[]'::jsonb,

    created_at timestamptz default now(),

    unique (menu_item_id, condition_id)
);

create table if not exists route_cache (
    id uuid primary key default gen_random_uuid(),
    origin_hash text not null,
    restaurant_id uuid not null references restaurants(id) on delete cascade,
    travel_mode text not null, 

    distance_meters integer,
    duration_seconds integer,

    cached_at timestamptz default now(),
    expires_at timestamptz,

    unique (origin_hash, restaurant_id, travel_mode)
);