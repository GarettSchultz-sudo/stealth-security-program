import { NextRequest, NextResponse } from 'next/server'

// Mock data for development - replace with actual database queries
const mockStats = {
  total_events: 1247,
  events_24h: 89,
  critical_count: 3,
  high_count: 12,
  medium_count: 34,
  low_count: 40,
  blocked_count: 8,
  alerted_count: 15,
  threat_breakdown: {
    prompt_injection: 45,
    credential_exposure: 12,
    data_exfiltration: 8,
    tool_abuse: 3,
    behavioral_anomaly: 15,
    custom: 6,
  },
  severity_breakdown: {
    critical: 3,
    high: 12,
    medium: 34,
    low: 40,
  },
}

export async function GET(request: NextRequest) {
  try {
    // In production, fetch from database
    // const supabase = createRouteHandlerClient()
    // const { data: events } = await supabase
    //   .from('security_events')
    //   .select('*')
    //   .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())

    // For now, return mock data
    return NextResponse.json(mockStats)
  } catch (error) {
    console.error('Error fetching security stats:', error)
    return NextResponse.json(
      { error: 'Failed to fetch security stats' },
      { status: 500 }
    )
  }
}
