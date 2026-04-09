create index if not exists idx_restaurants_name_lower
on restaurants (lower(name));

create index if not exists idx_restaurants_name
on restaurants (name);

create index if not exists idx_restaurants_chain_brand
on restaurants (chain_brand);

create index if not exists idx_restaurants_cuisine
on restaurants (cuisine);

create index if not exists idx_restaurants_lat_lng
on restaurants (lat, lng);

create index if not exists idx_restaurants_deep_status
on restaurants (deep_status);

create index if not exists idx_restaurants_last_discovered_at
on restaurants (last_discovered_at);

create index if not exists idx_restaurants_next_refresh_at
on restaurants (next_refresh_at);

create index if not exists idx_discovery_runs_started_at
on discovery_runs (started_at);

create index if not exists idx_discovery_runs_status
on discovery_runs (status);


create index if not exists idx_discovery_run_restaurants_restaurant_id
on discovery_run_restaurants (restaurant_id);


create index if not exists idx_restaurant_pages_restaurant_id
on restaurant_pages (restaurant_id);

create index if not exists idx_restaurant_pages_page_type
on restaurant_pages (page_type);

create index if not exists idx_restaurant_pages_last_fetched_at
on restaurant_pages (last_fetched_at);



create index if not exists idx_menu_items_restaurant_id
on menu_items (restaurant_id);

create index if not exists idx_menu_items_name
on menu_items (name);

create index if not exists idx_menu_items_category
on menu_items (category);

create index if not exists idx_menu_items_last_seen_at
on menu_items (last_seen_at);


create index if not exists idx_condition_evaluations_menu_item_id
on condition_evaluations (menu_item_id);

create index if not exists idx_condition_evaluations_condition_id
on condition_evaluations (condition_id);

create index if not exists idx_condition_evaluations_label
on condition_evaluations (label);


create index if not exists idx_route_cache_lookup
on route_cache (origin_hash, restaurant_id, travel_mode);

create index if not exists idx_route_cache_expires_at
on route_cache (expires_at);