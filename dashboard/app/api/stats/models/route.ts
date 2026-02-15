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

// GET - Get model breakdown data
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const days = parseInt(searchParams.get('days') || '7', 10)

    const supabase = getAdminClient()
    const now = new Date()

    // Calculate start date (N days ago)
    const startDate = new Date(now)
    startDate.setUTCDate(startDate.getUTCDate() - days)
    startDate.setUTCHours(0, 0, 0, 0)

    // Get all logs in the date range with model and latency info
    const { data: logs, error } = await supabase
      .from('request_logs')
      .select('model, cost_usd, latency_ms')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())

    if (error) {
      console.error('Error fetching model data:', error)
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Aggregate by model
    const modelData: Record<string, {
      model: string
      requests: number
      total_cost: number
      total_latency: number
    }> = {}

    for (const log of logs || []) {
      const model = log.model || 'unknown'
      if (!modelData[model]) {
        modelData[model] = {
          model,
          requests: 0,
          total_cost: 0,
          total_latency: 0,
        }
      }
      modelData[model].requests += 1
      modelData[model].total_cost += log.cost_usd || 0
      modelData[model].total_latency += log.latency_ms || 0
    }

    // Convert to array and calculate averages
    const breakdownData = Object.values(modelData)
      .map((item) => ({
        model: item.model,
        requests: item.requests,
        total_cost: Math.round(item.total_cost * 10000) / 10000, // Round to 4 decimal places
        avg_latency: item.requests > 0
          ? Math.round(item.total_latency / item.requests)
          : 0,
      }))
      .sort((a, b) => b.total_cost - a.total_cost) // Sort by cost descending

    return NextResponse.json({ data: breakdownData })
  } catch (error) {
    console.error('Error fetching model data:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
