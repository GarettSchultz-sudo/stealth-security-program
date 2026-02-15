-- Migration 004: Alerts Table
-- Creates table for alert configurations and notifications

-- ============================================================================
-- ALERTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    budget_id UUID REFERENCES public.budgets(id) ON DELETE SET NULL,

    -- Alert configuration
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN (
        'budget_warning',
        'budget_breach',
        'cost_spike',
        'error_rate',
        'agent_inactive'
    )),
    threshold_percent INTEGER DEFAULT 80,

    -- Delivery configuration
    delivery_method VARCHAR(50) NOT NULL DEFAULT 'email' CHECK (delivery_method IN (
        'email',
        'slack_webhook',
        'discord_webhook',
        'generic_webhook'
    )),
    delivery_config JSONB DEFAULT '{}',

    -- Status tracking
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,

    -- Cooldown to prevent spam
    cooldown_minutes INTEGER DEFAULT 60,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_alerts_user ON public.alerts(user_id);
CREATE INDEX idx_alerts_budget ON public.alerts(budget_id);
CREATE INDEX idx_alerts_type ON public.alerts(alert_type);
CREATE INDEX idx_alerts_active ON public.alerts(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own alerts" ON public.alerts
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on alerts" ON public.alerts
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER alerts_updated_at
    BEFORE UPDATE ON public.alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT ALL ON public.alerts TO authenticated;
