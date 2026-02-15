import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

async function getCurrentUser(request: NextRequest) {
  const cookieStore = await cookies()

  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => cookieStore.set(name, value))
      },
    },
  })

  const { data: { session } } = await supabase.auth.getSession()
  return session?.user
}

function getAdminClient() {
  return createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
    cookies: {
      getAll: () => [],
      setAll: () => {},
    },
  })
}

// Model downgrade hierarchy
const MODEL_HIERARCHY: Record<string, string[]> = {
  'claude-opus-4-6': ['claude-sonnet-4-5-20250929', 'claude-3-5-haiku-20241022'],
  'claude-3-opus-20240229': ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
  'gpt-4-turbo': ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4o': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4o-mini': ['gpt-3.5-turbo'],
}

/**
 * GET /api/budget/status - Get real-time budget status
 */
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const budgetId = searchParams.get('budgetId')
    const currentModel = searchParams.get('model') || 'gpt-4o'

    const supabase = getAdminClient()

    // Fetch budgets
    let query = supabase
      .from('budgets')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true)

    if (budgetId) {
      query = query.eq('id', budgetId)
    }

    const { data: budgets, error } = await query.order('created_at', { ascending: false })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Get active request count (simplified - in production, use Redis)
    const { count: activeRequests } = await supabase
      .from('request_logs')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .gte('created_at', new Date(Date.now() - 60000).toISOString()) // Last minute

    // Build response for each budget
    const budgetStatuses = (budgets || []).map((budget) => {
      const percentUsed = (budget.current_spend_usd / budget.limit_usd) * 100
      const remaining = Math.max(0, budget.limit_usd - budget.current_spend_usd)

      // Determine recommended action
      let recommendedAction: 'continue' | 'downgrade' | 'block' = 'continue'
      if (percentUsed >= 100) recommendedAction = 'block'
      else if (percentUsed >= 90) recommendedAction = 'downgrade'

      // Get recommended model based on current usage
      const recommendedModel = MODEL_HIERARCHY[currentModel]?.[0] || null

      // Estimate remaining requests (simplified)
      const avgCostPerRequest = 0.002 // Approximate
      const estimatedRemainingRequests = Math.floor(remaining / avgCostPerRequest)

      return {
        budgetId: budget.id,
        name: budget.name,
        limit: budget.limit_usd,
        current: budget.current_spend_usd,
        percentUsed: Math.round(percentUsed * 100) / 100,
        remaining,
        period: budget.period,
        scope: budget.scope,
        scopeIdentifier: budget.scope_identifier,
        actionOnBreach: budget.action_on_breach,
        resetAt: budget.reset_at,
        isActive: budget.is_active,
        recommendedAction,
        recommendedModel: percentUsed >= 90 ? recommendedModel : null,
        downgradeAvailable: !!MODEL_HIERARCHY[currentModel],
        estimatedRemainingRequests,
        activeRequests: activeRequests || 0,
      }
    })

    // Calculate totals
    const totalLimit = budgetStatuses.reduce((sum, b) => sum + b.limit, 0)
    const totalSpent = budgetStatuses.reduce((sum, b) => sum + b.current, 0)
    const breachedCount = budgetStatuses.filter((b) => b.percentUsed >= 100).length

    return NextResponse.json({
      budgets: budgetStatuses,
      summary: {
        totalBudgets: budgetStatuses.length,
        totalLimit,
        totalSpent,
        totalRemaining: totalLimit - totalSpent,
        breachedCount,
        anyBreached: breachedCount > 0,
        allBreached: breachedCount === budgetStatuses.length && budgetStatuses.length > 0,
      },
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('Error fetching budget status:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
