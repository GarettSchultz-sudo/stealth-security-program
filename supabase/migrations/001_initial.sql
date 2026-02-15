-- AgentCostControl Initial Schema
-- Run this in Supabase SQL Editor

-- Enable necessary extensions
create extension if not exists "uuid-ossp";
create extension if not exists pg_trgm;  -- For text search

-- Users table (synced with Supabase Auth)
create table public.users (
    id uuid references auth.users on delete cascade primary key,
    email text unique not null,
    plan text default 'free' check (plan in ('free', 'pro', 'team')),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- API Keys table
create table public.api_keys (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    key_hash text not null,  -- SHA-256 hash of key
    name text,
    last_used_at timestamptz,
    created_at timestamptz default now(),
    is_active boolean default true
);

-- API Logs table (partitioned by month for performance)
create table public.api_logs (
    id uuid default uuid_generate_v4(),
    user_id uuid references public.users(id) on delete cascade not null,
    api_key_id uuid references public.api_keys(id),
    timestamp timestamptz default now(),
    provider text not null,  -- anthropic, openai, google, etc.
    model text not null,
    request_tokens int not null,
    response_tokens int not null,
    total_tokens int generated always as (request_tokens + response_tokens) stored,
    cost_usd decimal(10,6) not null,
    latency_ms int,
    status_code int,
    error_message text,
    metadata jsonb default '{}',
    is_streaming boolean default false,
    cache_creation_tokens int default 0,
    cache_read_tokens int default 0,
    
    primary key (id, timestamp)
) partition by range (timestamp);

-- Create initial partitions (current and next 2 months)
create table api_logs_2026_02 partition of api_logs
    for values from ('2026-02-01') to ('2026-03-01');
create table api_logs_2026_03 partition of api_logs
    for values from ('2026-03-01') to ('2026-04-01');
create table api_logs_2026_04 partition of api_logs
    for values from ('2026-04-01') to ('2026-05-01');

-- Indexes for fast queries
create index idx_api_logs_user_time on api_logs(user_id, timestamp desc);
create index idx_api_logs_model on api_logs(model, timestamp desc);
create index idx_api_logs_provider on api_logs(provider, timestamp desc);

-- Budgets table
create table public.budgets (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    name text not null,
    period text check (period in ('daily', 'weekly', 'monthly')),
    limit_usd decimal(10,2) not null,
    current_spend_usd decimal(10,2) default 0,
    reset_at timestamptz,
    scope text default 'global' check (scope in ('global', 'agent', 'model', 'workflow')),
    scope_identifier text,  -- agent_id, model_name, or workflow_name
    action_on_breach text default 'alert' check (action_on_breach in ('alert', 'block', 'downgrade')),
    is_active boolean default true,
    created_at timestamptz default now()
);

-- Routing Rules table
create table public.routing_rules (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    name text not null,
    priority int default 0,
    source_model_pattern text,  -- Regex pattern
    target_model text not null,
    min_messages int,
    content_keywords text[],  -- Array of keywords
    reason text,
    is_active boolean default true,
    created_at timestamptz default now()
);

-- Row Level Security (RLS)
alter table public.users enable row level security;
alter table public.api_keys enable row level security;
alter table public.api_logs enable row level security;
alter table public.budgets enable row level security;
alter table public.routing_rules enable row level security;

-- RLS Policies
create policy "Users can view own profile"
    on public.users for select
    using (auth.uid() = id);

create policy "Users can update own profile"
    on public.users for update
    using (auth.uid() = id);

create policy "Users can manage own API keys"
    on public.api_keys for all
    using (auth.uid() = user_id);

create policy "Users can view own logs"
    on public.api_logs for select
    using (auth.uid() = user_id);

create policy "Service role can insert logs"
    on public.api_logs for insert
    with check (true);

create policy "Users can manage own budgets"
    on public.budgets for all
    using (auth.uid() = user_id);

create policy "Users can manage own routing rules"
    on public.routing_rules for all
    using (auth.uid() = user_id);

-- Updated at trigger
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger update_users_updated_at
    before update on public.users
    for each row
    execute function update_updated_at();

-- Analytics functions
create or replace function get_today_spend(p_user_id uuid default auth.uid())
returns decimal as $$
    select coalesce(sum(cost_usd), 0)
    from api_logs
    where date_trunc('day', timestamp) = date_trunc('day', now())
    and user_id = p_user_id;
$$ language sql security definer;

create or replace function get_spend_by_day(p_days int default 30, p_user_id uuid default auth.uid())
returns table(date text, spend decimal, requests bigint) as $$
    select 
        date_trunc('day', timestamp)::date::text as date,
        coalesce(sum(cost_usd), 0) as spend,
        count(*) as requests
    from api_logs
    where timestamp >= now() - interval '1 day' * p_days
    and user_id = p_user_id
    group by date_trunc('day', timestamp)
    order by date;
$$ language sql security definer;

create or replace function get_model_breakdown(p_days int default 7, p_user_id uuid default auth.uid())
returns table(model text, requests bigint, total_cost decimal, avg_latency int) as $$
    select 
        model,
        count(*) as requests,
        sum(cost_usd) as total_cost,
        avg(latency_ms)::int as avg_latency
    from api_logs
    where timestamp >= now() - interval '1 day' * p_days
    and user_id = p_user_id
    group by model
    order by total_cost desc;
$$ language sql security definer;
