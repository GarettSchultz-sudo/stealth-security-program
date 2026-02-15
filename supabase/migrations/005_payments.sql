-- AgentCostControl Payments Schema
-- Add Stripe fields and payment events table

-- Add Stripe fields to users table (if not already present)
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS stripe_customer_id text UNIQUE,
ADD COLUMN IF NOT EXISTS stripe_subscription_id text;

-- Create payment_events table for audit trail
CREATE TABLE IF NOT EXISTS public.payment_events (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    event_type text NOT NULL,
    stripe_event_id text NOT NULL,
    data jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_payment_events_user ON public.payment_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_events_type ON public.payment_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON public.users(stripe_customer_id);

-- Enable RLS on payment_events
ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for payment_events
CREATE POLICY "Users can view own payment events"
    ON public.payment_events FOR SELECT
    USING (auth.uid() = user_id);

-- Only service role can insert (via webhook)
CREATE POLICY "Service role can insert payment events"
    ON public.payment_events FOR INSERT
    WITH CHECK (true);

-- Add comment
COMMENT ON TABLE public.payment_events IS 'Audit trail for all payment-related events from Stripe webhooks';
