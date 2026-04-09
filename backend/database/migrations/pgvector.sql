create extension if not exists vector;


create table if not exists menu_item_embeddings (
    menu_item_id uuid primary key references menu_items(id) on delete cascade,
    embedding vector(768),
    created_at timestamptz default now()
);


create index if not exists idx_menu_item_embeddings_hnsw
on menu_item_embeddings
using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

create or replace function match_menu_items (
    query_embedding vector(768),
    match_count integer default 10
)
returns table (
    menu_item_id uuid,
    similarity double precision
)
language sql
stable
as $$
    select
        menu_item_id,
        1 - (embedding <=> query_embedding) as similarity
    from menu_item_embeddings
    order by embedding <=> query_embedding
    limit match_count;
$$;