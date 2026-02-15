-- Migration 003: Agent Tasks Tracking
-- Creates tables for agent registration, task tracking, and utilization metrics

-- ============================================================================
-- AGENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_type VARCHAR(100), -- 'claude-code', 'cursor', 'aider', 'custom', etc.
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,

    -- Configuration
    default_model VARCHAR(255),
    default_provider VARCHAR(100),
    budget_limit DECIMAL(10, 4), -- Optional per-agent budget
    tags TEXT[], -- ['coding', 'research', 'chat']

    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'paused', 'disabled'
    last_heartbeat TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,

    -- Metrics (aggregated)
    total_requests INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(12, 6) DEFAULT 0,
    total_tasks_completed INTEGER DEFAULT 0,
    total_tasks_failed INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('active', 'paused', 'disabled'))
);

-- Index for quick lookups
CREATE INDEX idx_agents_status ON public.agents(status);
CREATE INDEX idx_agents_type ON public.agents(agent_type);
CREATE INDEX idx_agents_last_seen ON public.agents(last_seen DESC);

-- ============================================================================
-- AGENT TASKS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,

    -- Task identification
    task_id VARCHAR(255) NOT NULL, -- Client-provided task ID
    task_type VARCHAR(100), -- 'coding', 'research', 'chat', 'analysis', etc.
    title VARCHAR(500),
    description TEXT,

    -- Task hierarchy
    parent_task_id UUID REFERENCES public.agent_tasks(id) ON DELETE SET NULL,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',
    -- 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled'

    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),

    -- Model usage
    model VARCHAR(255),
    provider VARCHAR(100),

    -- Metrics
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    api_calls INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT, -- Computed or set on completion

    -- Results
    result_summary TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}', -- Flexible storage for task-specific data

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_agent_task UNIQUE (agent_id, task_id),
    CONSTRAINT valid_task_status CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'))
);

-- Indexes for task queries
CREATE INDEX idx_agent_tasks_agent ON public.agent_tasks(agent_id);
CREATE INDEX idx_agent_tasks_status ON public.agent_tasks(status);
CREATE INDEX idx_agent_tasks_created ON public.agent_tasks(created_at DESC);
CREATE INDEX idx_agent_tasks_active ON public.agent_tasks(agent_id, status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_agent_tasks_parent ON public.agent_tasks(parent_task_id);

-- ============================================================================
-- AGENT HEARTBEATS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agent_heartbeats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,

    -- Current state
    current_task_id UUID REFERENCES public.agent_tasks(id),
    status VARCHAR(50) DEFAULT 'idle', -- 'idle', 'busy', 'error'

    -- System info
    cpu_percent DECIMAL(5, 2),
    memory_mb INTEGER,
    queue_depth INTEGER DEFAULT 0,

    -- Timestamp
    recorded_at TIMESTAMPTZ DEFAULT NOW(),

    -- Additional data
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_heartbeats_agent ON public.agent_heartbeats(agent_id, recorded_at DESC);

-- ============================================================================
-- TASK EVENTS TABLE (Audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.task_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES public.agent_tasks(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,

    event_type VARCHAR(100) NOT NULL, -- 'started', 'progress', 'model_call', 'completed', 'failed'
    event_data JSONB DEFAULT '{}',

    -- Associated API call (if applicable)
    api_log_id UUID,

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_task_events_task ON public.task_events(task_id, recorded_at DESC);
CREATE INDEX idx_task_events_type ON public.task_events(event_type);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_heartbeats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_events ENABLE ROW LEVEL SECURITY;

-- Agents: Users can see their own agents (via api_key ownership)
CREATE POLICY "Users can view their own agents" ON public.agents
    FOR SELECT USING (
        api_key_id IN (SELECT id FROM public.api_keys WHERE user_id = auth.uid())
    );

CREATE POLICY "Service role full access on agents" ON public.agents
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Agent Tasks: Same policy
CREATE POLICY "Users can view their own tasks" ON public.agent_tasks
    FOR SELECT USING (
        agent_id IN (SELECT id FROM public.agents WHERE api_key_id IN (SELECT id FROM public.api_keys WHERE user_id = auth.uid()))
    );

CREATE POLICY "Service role full access on tasks" ON public.agent_tasks
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Heartbeats
CREATE POLICY "Users can view their own heartbeats" ON public.agent_heartbeats
    FOR SELECT USING (
        agent_id IN (SELECT id FROM public.agents WHERE api_key_id IN (SELECT id FROM public.api_keys WHERE user_id = auth.uid()))
    );

-- Task Events
CREATE POLICY "Users can view their own events" ON public.task_events
    FOR SELECT USING (
        agent_id IN (SELECT id FROM public.agents WHERE api_key_id IN (SELECT id FROM public.api_keys WHERE user_id = auth.uid()))
    );

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agents_updated_at
    BEFORE UPDATE ON public.agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER agent_tasks_updated_at
    BEFORE UPDATE ON public.agent_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update agent metrics on task completion
CREATE OR REPLACE FUNCTION update_agent_metrics()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        UPDATE public.agents
        SET total_tasks_completed = total_tasks_completed + 1,
            total_tokens = total_tokens + NEW.input_tokens + NEW.output_tokens,
            total_cost_usd = total_cost_usd + NEW.cost_usd,
            last_seen = NOW()
        WHERE id = NEW.agent_id;
    ELSIF NEW.status = 'failed' THEN
        UPDATE public.agents
        SET total_tasks_failed = total_tasks_failed + 1,
            last_seen = NOW()
        WHERE id = NEW.agent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_completion_trigger
    AFTER UPDATE OF status ON public.agent_tasks
    FOR EACH ROW
    WHEN (OLD.status NOT IN ('completed', 'failed') AND NEW.status IN ('completed', 'failed'))
    EXECUTE FUNCTION update_agent_metrics();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active tasks view
CREATE OR REPLACE VIEW public.active_tasks AS
SELECT
    t.id,
    t.task_id,
    t.title,
    t.status,
    t.progress_percent,
    t.model,
    t.cost_usd,
    t.started_at,
    t.created_at,
    EXTRACT(EPOCH FROM (NOW() - t.started_at)) * 1000 as duration_ms,
    a.name as agent_name,
    a.agent_type,
    a.id as agent_id
FROM public.agent_tasks t
JOIN public.agents a ON t.agent_id = a.id
WHERE t.status IN ('pending', 'running')
ORDER BY t.created_at DESC;

-- Agent utilization summary
CREATE OR REPLACE VIEW public.agent_utilization AS
SELECT
    a.id,
    a.name,
    a.agent_type,
    a.status as agent_status,
    a.last_heartbeat,
    a.last_seen,
    a.total_requests,
    a.total_tokens,
    a.total_cost_usd,
    a.total_tasks_completed,
    a.total_tasks_failed,
    COUNT(t.id) FILTER (WHERE t.status IN ('pending', 'running')) as active_tasks,
    COUNT(t.id) FILTER (WHERE t.status = 'completed' AND t.completed_at > NOW() - INTERVAL '24 hours') as tasks_24h,
    SUM(t.cost_usd) FILTER (WHERE t.completed_at > NOW() - INTERVAL '24 hours') as cost_24h
FROM public.agents a
LEFT JOIN public.agent_tasks t ON a.id = t.agent_id
GROUP BY a.id
ORDER BY a.last_seen DESC;

-- ============================================================================
-- SEED DATA (Optional demo agents)
-- ============================================================================

-- Insert a demo agent for testing
INSERT INTO public.agents (id, name, description, agent_type, status, tags)
VALUES
    (gen_random_uuid(), 'Demo Agent', 'A demonstration agent for testing', 'demo', 'active', ARRAY['testing'])
ON CONFLICT DO NOTHING;
