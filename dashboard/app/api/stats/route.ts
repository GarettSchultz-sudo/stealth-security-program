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

// GET - Get dashboard statistics
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const supabase = getAdminClient()
    const now = new Date()

    // Today's date range (UTC)
    const todayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
    const todayEnd = new Date(todayStart)
    todayEnd.setUTCDate(todayEnd.getUTCDate() + 1)

    // This month's date range
    const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1))
    const monthEnd = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1))

    // Yesterday's date range
    const yesterdayStart = new Date(todayStart)
    yesterdayStart.setUTCDate(yesterdayStart.getUTCDate() - 1)
    const yesterdayEnd = new Date(todayStart)

    // Get today's spend
    const { data: todayLogs } = await supabase
      .from('request_logs')
      .select('cost_usd')
      .eq('user_id', user.id)
      .gte('created_at', todayStart.toISOString())
      .lt('created_at', todayEnd.toISOString())

    const todaySpend = todayLogs?.reduce((sum, log) => sum + (log.cost_usd || 0), 0) || 0

    // Get yesterday's spend
    const { data: yesterdayLogs } = await supabase
      .from('request_logs')
      .select('cost_usd')
      .eq('user_id', user.id)
      .gte('created_at', yesterdayStart.toISOString())
      .lt('created_at', yesterdayEnd.toISOString())

    const yesterdaySpend = yesterdayLogs?.reduce((sum, log) => sum + (log.cost_usd || 0), 0) || 0

    // Get month spend
    const { data: monthLogs } = await supabase
      .from('request_logs')
      .select('cost_usd')
      .eq('user_id', user.id)
      .gte('created_at', monthStart.toISOString())
      .lt('created_at', monthEnd.toISOString())

    const monthSpend = monthLogs?.reduce((sum, log) => sum + (log.cost_usd || 0), 0) || 0

    // Get total requests this month
    const { count: monthRequests } = await supabase
      .from('request_logs')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .gte('created_at', monthStart.toISOString())
      .lt('created_at', monthEnd.toISOString())

    // Calculate trend (percentage change from yesterday)
    const trend = yesterdaySpend > 0
      ? ((todaySpend - yesterdaySpend) / yesterdaySpend) * 100
      : 0

    // Calculate average cost per request
    const avgCostPerRequest = (monthRequests || 0) > 0
      ? monthSpend / (monthRequests || 1)
      : 0

    return NextResponse.json({
      todaySpend,
      yesterdaySpend,
      monthSpend,
      monthRequests: monthRequests || 0,
      avgCostPerRequest,
      trend: Math.round(trend * 100) / 100,
    })
  } catch (error) {
    console.error('Error fetching stats:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
