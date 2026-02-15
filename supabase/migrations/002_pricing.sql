-- Pricing Table Schema
-- Run after 001_initial.sql

-- Pricing table (versioned)
create table public.pricing (
    id uuid default uuid_generate_v4() primary key,
    provider text not null,
    model text not null,
    input_price_per_mtok decimal(10,6) not null,  -- Price per 1M input tokens
    output_price_per_mtok decimal(10,6) not null, -- Price per 1M output tokens
    cache_creation_price_per_mtok decimal(10,6) default 0,
    cache_read_price_per_mtok decimal(10,6) default 0,
    effective_from date not null,
    effective_to date,
    unique(provider, model, effective_from)
);

-- Index for fast pricing lookups
create index idx_pricing_lookup on pricing(provider, model, effective_from desc);

-- Pricing is readable by all authenticated users
alter table public.pricing enable row level security;

create policy "Pricing is readable by all"
    on public.pricing for select
    to authenticated
    using (true);
