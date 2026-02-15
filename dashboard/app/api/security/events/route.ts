import { NextRequest, NextResponse } from 'next/server'

// Mock events for development
const mockEvents = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    threat_type: 'prompt_injection',
    severity: 'high' as const,
    confidence: 0.92,
    description: 'System prompt override attempt detected',
    agent_id: '550e8400-e29b-41d4-a716-446655440000',
    action_taken: 'block',
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    threat_type: 'credential_exposure',
    severity: 'critical' as const,
    confidence: 0.98,
    description: 'AWS access key detected in request',
    agent_id: '550e8400-e29b-41d4-a716-446655440001',
    action_taken: 'block',
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    threat_type: 'behavioral_anomaly',
    severity: 'medium' as const,
    confidence: 0.75,
    description: 'Unusual request volume detected (5x baseline)',
    agent_id: '550e8400-e29b-41d4-a716-446655440002',
    action_taken: 'alert',
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    threat_type: 'data_exfiltration',
    severity: 'high' as const,
    confidence: 0.88,
    description: 'Large response with PII patterns detected',
    agent_id: '550e8400-e29b-41d4-a716-446655440003',
    action_taken: 'alert',
  },
  {
    id: '5',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    threat_type: 'tool_abuse',
    severity: 'medium' as const,
    confidence: 0.82,
    description: 'Suspicious shell command pattern detected',
    agent_id: '550e8400-e29b-41d4-a716-446655440004',
    action_taken: 'warn',
  },
]

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const orgId = searchParams.get('org_id')
    const severity = searchParams.get('severity')
    const threatType = searchParams.get('threat_type')

    // In production, fetch from database with filters
    // const supabase = createRouteHandlerClient()
    // let query = supabase
    //   .from('security_events')
    //   .select('*')
    //   .order('created_at', { ascending: false })
    //   .limit(limit)
    //
    // if (orgId) query = query.eq('org_id', orgId)
    // if (severity) query = query.eq('severity', severity)
    // if (threatType) query = query.eq('threat_type', threatType)

    // Filter mock data
    let events = [...mockEvents]
    if (severity) {
      events = events.filter((e) => e.severity === severity)
    }
    if (threatType) {
      events = events.filter((e) => e.threat_type === threatType)
    }

    return NextResponse.json({
      events: events.slice(0, limit),
      total: events.length,
    })
  } catch (error) {
    console.error('Error fetching security events:', error)
    return NextResponse.json(
      { error: 'Failed to fetch security events' },
      { status: 500 }
    )
  }
}
