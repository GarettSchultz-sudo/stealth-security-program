import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Types
export interface ApiLog {
  id: string
  user_id: string
  provider: string
  model: string
  request_tokens: number
  response_tokens: number
  cost_usd: number
  latency_ms: number
  timestamp: string
  metadata?: Record<string, any>
}

export interface Budget {
  id: string
  name: string
  period: 'daily' | 'weekly' | 'monthly'
  limit_usd: number
  current_spend_usd: number
  scope: 'global' | 'agent' | 'model' | 'workflow'
  action_on_breach: 'alert' | 'block' | 'downgrade'
  is_active: boolean
}

export interface RoutingRule {
  id: string
  name: string
  source_model_pattern?: string
  target_model: string
  priority: number
  reason?: string
  is_active: boolean
}
