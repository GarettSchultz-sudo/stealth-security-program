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

// GET - Get daily spend chart data
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

    // Get all logs in the date range
    const { data: logs, error } = await supabase
      .from('request_logs')
      .select('cost_usd, created_at')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: true })

    if (error) {
      console.error('Error fetching chart data:', error)
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Group by date
    const dailyData: Record<string, { spend: number; requests: number }> = {}

    // Initialize all dates in range with zeros
    for (let i = 0; i <= days; i++) {
      const date = new Date(startDate)
      date.setUTCDate(date.getUTCDate() + i)
      const dateKey = date.toISOString().split('T')[0]
      dailyData[dateKey] = { spend: 0, requests: 0 }
    }

    // Aggregate logs by date
    for (const log of logs || []) {
      const dateKey = log.created_at.split('T')[0]
      if (dailyData[dateKey]) {
        dailyData[dateKey].spend += log.cost_usd || 0
        dailyData[dateKey].requests += 1
      }
    }

    // Convert to array format for charts
    const chartData = Object.entries(dailyData)
      .map(([date, data]) => ({
        date,
        spend: Math.round(data.spend * 10000) / 10000, // Round to 4 decimal places
        requests: data.requests,
      }))
      .sort((a, b) => a.date.localeCompare(b.date))

    return NextResponse.json({ data: chartData })
  } catch (error) {
    console.error('Error fetching chart data:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
