-- Migration 006: Fix RLS policies for scan_credits and users
-- This allows users to create their own records when they first start scanning

-- Add INSERT policy for users table (so users can create their own profile)
CREATE POLICY "Users can insert own profile"
    ON public.users FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Add INSERT policy for scan_credits
CREATE POLICY "Users can insert own credits"
    ON public.scan_credits FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Add UPDATE policy for scan_credits (for consuming credits)
CREATE POLICY "Users can update own credits"
    ON public.scan_credits FOR UPDATE
    USING (auth.uid() = user_id);
