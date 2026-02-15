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

// GET - Get agent breakdown data
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

    // Get all logs in the date range with agent info
    const { data: logs, error } = await supabase
      .from('request_logs')
      .select('agent_id, cost_usd, total_tokens, latency_ms')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())

    if (error) {
      console.error('Error fetching agent data:', error)
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Get agent names from agents table
    const agentIds = [...new Set(logs?.filter(l => l.agent_id).map(l => l.agent_id) || [])]
    const { data: agents } = await supabase
      .from('agents')
      .select('id, name')
      .in('id', agentIds)

    const agentNames: Record<string, string> = {}
    for (const agent of agents || []) {
      agentNames[agent.id] = agent.name
    }

    // Aggregate by agent
    const agentData: Record<string, {
      agent_id: string | null
      agent_name: string
      spend_usd: number
      requests: number
      tokens: number
      total_latency: number
    }> = {}

    let totalSpend = 0

    for (const log of logs || []) {
      const agentKey = log.agent_id || 'unassigned'
      if (!agentData[agentKey]) {
        agentData[agentKey] = {
          agent_id: log.agent_id,
          agent_name: log.agent_id
            ? (agentNames[log.agent_id] || `Agent ${log.agent_id.slice(0, 8)}`)
            : 'Unassigned',
          spend_usd: 0,
          requests: 0,
          tokens: 0,
          total_latency: 0,
        }
      }
      agentData[agentKey].requests += 1
      agentData[agentKey].spend_usd += log.cost_usd || 0
      agentData[agentKey].tokens += log.total_tokens || 0
      agentData[agentKey].total_latency += log.latency_ms || 0
      totalSpend += log.cost_usd || 0
    }

    // Convert to array and calculate averages
    const breakdownData = Object.values(agentData)
      .map((item) => ({
        agent_id: item.agent_id,
        agent_name: item.agent_name,
        spend_usd: Math.round(item.spend_usd * 10000) / 10000,
        requests: item.requests,
        tokens: item.tokens,
        avg_latency_ms: item.requests > 0
          ? Math.round(item.total_latency / item.requests)
          : 0,
        percent_of_total: totalSpend > 0
          ? Math.round((item.spend_usd / totalSpend) * 10000) / 100
          : 0,
      }))
      .sort((a, b) => b.spend_usd - a.spend_usd)

    return NextResponse.json(breakdownData)
  } catch (error) {
    console.error('Error fetching agent data:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
