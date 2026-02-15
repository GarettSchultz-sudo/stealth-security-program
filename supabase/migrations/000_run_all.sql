-- ============================================
-- AgentCostControl - All Migrations Combined
-- Run this entire file in Supabase SQL Editor
-- ============================================

-- Enable necessary extensions
create extension if not exists "uuid-ossp";
create extension if not exists pg_trgm;

-- ============================================================================
-- PART 1: INITIAL SCHEMA (001_initial.sql)
-- ============================================================================

-- Users table (synced with Supabase Auth)
create table if not exists public.users (
    id uuid references auth.users on delete cascade primary key,
    email text unique not null,
    plan text default 'free' check (plan in ('free', 'pro', 'team')),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- API Keys table
create table if not exists public.api_keys (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    key_hash text not null,
    name text,
    last_used_at timestamptz,
    created_at timestamptz default now(),
    is_active boolean default true
);

-- API Logs table (partitioned by month)
create table if not exists public.api_logs (
    id uuid default uuid_generate_v4(),
    user_id uuid references public.users(id) on delete cascade not null,
    api_key_id uuid references public.api_keys(id),
    timestamp timestamptz default now(),
    provider text not null,
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

-- Create partitions for api_logs
create table if not exists api_logs_2026_02 partition of api_logs
    for values from ('2026-02-01') to ('2026-03-01');
create table if not exists api_logs_2026_03 partition of api_logs
    for values from ('2026-03-01') to ('2026-04-01');
create table if not exists api_logs_2026_04 partition of api_logs
    for values from ('2026-04-01') to ('2026-05-01');

-- Indexes
create index if not exists idx_api_logs_user_time on api_logs(user_id, timestamp desc);
create index if not exists idx_api_logs_model on api_logs(model, timestamp desc);
create index if not exists idx_api_logs_provider on api_logs(provider, timestamp desc);

-- Budgets table
create table if not exists public.budgets (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    name text not null,
    period text check (period in ('daily', 'weekly', 'monthly')),
    limit_usd decimal(10,2) not null,
    current_spend_usd decimal(10,2) default 0,
    reset_at timestamptz,
    scope text default 'global' check (scope in ('global', 'agent', 'model', 'workflow')),
    scope_identifier text,
    action_on_breach text default 'alert' check (action_on_breach in ('alert', 'block', 'downgrade')),
    is_active boolean default true,
    created_at timestamptz default now()
);

-- Routing Rules table
create table if not exists public.routing_rules (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    name text not null,
    priority int default 0,
    source_model_pattern text,
    target_model text not null,
    min_messages int,
    content_keywords text[],
    reason text,
    is_active boolean default true,
    created_at timestamptz default now()
);

-- ============================================================================
-- PART 2: PRICING TABLE (002_pricing.sql)
-- ============================================================================

create table if not exists public.pricing (
    id uuid default uuid_generate_v4() primary key,
    provider text not null,
    model text not null,
    input_price_per_mtok decimal(10,6) not null,
    output_price_per_mtok decimal(10,6) not null,
    cache_creation_price_per_mtok decimal(10,6) default 0,
    cache_read_price_per_mtok decimal(10,6) default 0,
    effective_from date not null,
    effective_to date,
    unique(provider, model, effective_from)
);

create index if not exists idx_pricing_lookup on pricing(provider, model, effective_from desc);

-- ============================================================================
-- PART 3: AGENT TASKS (003_agent_tasks.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_type VARCHAR(100),
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,
    default_model VARCHAR(255),
    default_provider VARCHAR(100),
    budget_limit DECIMAL(10, 4),
    tags TEXT[],
    status VARCHAR(50) DEFAULT 'active',
    last_heartbeat TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    total_requests INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(12, 6) DEFAULT 0,
    total_tasks_completed INTEGER DEFAULT 0,
    total_tasks_failed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('active', 'paused', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON public.agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_type ON public.agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON public.agents(last_seen DESC);

CREATE TABLE IF NOT EXISTS public.agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL,
    task_type VARCHAR(100),
    title VARCHAR(500),
    description TEXT,
    parent_task_id UUID REFERENCES public.agent_tasks(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    model VARCHAR(255),
    provider VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT,
    result_summary TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_agent_task UNIQUE (agent_id, task_id),
    CONSTRAINT valid_task_status CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON public.agent_tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON public.agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_created ON public.agent_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_active ON public.agent_tasks(agent_id, status) WHERE status IN ('pending', 'running');

-- ============================================================================
-- ANALYTICS FUNCTIONS
-- ============================================================================

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

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

alter table public.users enable row level security;
alter table public.api_keys enable row level security;
alter table public.api_logs enable row level security;
alter table public.budgets enable row level security;
alter table public.routing_rules enable row level security;
alter table public.pricing enable row level security;
alter table public.agents enable row level security;
alter table public.agent_tasks enable row level security;

-- RLS Policies
create policy "Users can view own profile" on public.users for select using (auth.uid() = id);
create policy "Users can update own profile" on public.users for update using (auth.uid() = id);
create policy "Users can manage own API keys" on public.api_keys for all using (auth.uid() = user_id);
create policy "Users can view own logs" on public.api_logs for select using (auth.uid() = user_id);
create policy "Service role can insert logs" on public.api_logs for insert with check (true);
create policy "Users can manage own budgets" on public.budgets for all using (auth.uid() = user_id);
create policy "Users can manage own routing rules" on public.routing_rules for all using (auth.uid() = user_id);
create policy "Pricing is readable by all" on public.pricing for select to authenticated using (true);

-- ============================================================================
-- UPDATED AT TRIGGER
-- ============================================================================

create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger update_users_updated_at before update on public.users for each row execute function update_updated_at();

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

SELECT 'AgentCostControl schema created successfully!' as status;
