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

// GET - Get provider breakdown data
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const days = parseInt(searchParams.get('days') || '30', 10)

    const supabase = getAdminClient()
    const now = new Date()

    // Calculate start date (N days ago)
    const startDate = new Date(now)
    startDate.setUTCDate(startDate.getUTCDate() - days)
    startDate.setUTCHours(0, 0, 0, 0)

    // Get all logs in the date range with provider info
    const { data: logs, error } = await supabase
      .from('request_logs')
      .select('provider, model, cost_usd, total_tokens')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())

    if (error) {
      console.error('Error fetching provider data:', error)
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Aggregate by provider
    const providerData: Record<string, {
      provider: string
      spend_usd: number
      requests: number
      tokens: number
      models: Set<string>
    }> = {}

    let totalSpend = 0

    for (const log of logs || []) {
      const provider = log.provider || 'unknown'
      if (!providerData[provider]) {
        providerData[provider] = {
          provider,
          spend_usd: 0,
          requests: 0,
          tokens: 0,
          models: new Set(),
        }
      }
      providerData[provider].requests += 1
      providerData[provider].spend_usd += log.cost_usd || 0
      providerData[provider].tokens += log.total_tokens || 0
      if (log.model) {
        providerData[provider].models.add(log.model)
      }
      totalSpend += log.cost_usd || 0
    }

    // Convert to array and calculate percentages
    const breakdownData = Object.values(providerData)
      .map((item) => ({
        provider: item.provider,
        spend_usd: Math.round(item.spend_usd * 10000) / 10000,
        requests: item.requests,
        tokens: item.tokens,
        model_count: item.models.size,
        percent_of_total: totalSpend > 0
          ? Math.round((item.spend_usd / totalSpend) * 10000) / 100
          : 0,
      }))
      .sort((a, b) => b.spend_usd - a.spend_usd)

    return NextResponse.json(breakdownData)
  } catch (error) {
    console.error('Error fetching provider data:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
