import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

// List monitored skills
export async function GET() {
  try {
    const supabase = await createSupabaseServerClient()

    // Get the current user
    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    const { data: monitored, error } = await supabase
      .from('monitored_skills')
      .select(`
        id,
        status,
        check_interval_seconds,
        last_check_at,
        next_check_at,
        baseline_trust_score,
        total_checks,
        findings_detected,
        alerts_sent,
        skill:clawhub_skills (
          skill_id,
          name
        )
      `)
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching monitored skills:', error)
      return NextResponse.json(
        { detail: 'Failed to fetch monitored skills' },
        { status: 500 }
      )
    }

    // Transform to expected format
    const formatted = (monitored || []).map((m: any) => ({
      id: m.id,
      skill_id: m.skill?.skill_id || 'unknown',
      skill_name: m.skill?.name || 'Unknown',
      status: m.status,
      check_interval_seconds: m.check_interval_seconds,
      last_check_at: m.last_check_at,
      next_check_at: m.next_check_at,
      baseline_trust_score: m.baseline_trust_score,
      findings_detected: m.findings_detected,
      alerts_sent: m.alerts_sent,
    }))

    return NextResponse.json(formatted)
  } catch (error) {
    console.error('Error in monitoring GET:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Start monitoring a skill
export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient()

    // Get the current user
    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    const body = await request.json()
    const { skill_id, check_interval_seconds = 3600, alert_on_critical = true, alert_on_high = true } = body

    if (!skill_id) {
      return NextResponse.json(
        { detail: 'skill_id is required' },
        { status: 400 }
      )
    }

    // Get or create skill record
    let skillRecord
    const { data: existingSkill } = await supabase
      .from('clawhub_skills')
      .select('id')
      .eq('skill_id', skill_id)
      .single()

    if (existingSkill) {
      skillRecord = existingSkill
    } else {
      const { data: newSkill, error: createError } = await supabase
        .from('clawhub_skills')
        .insert({
          skill_id,
          name: skill_id.split('/').pop() || skill_id,
        })
        .select('id')
        .single()

      if (createError) {
        return NextResponse.json(
          { detail: 'Failed to create skill record' },
          { status: 500 }
        )
      }
      skillRecord = newSkill
    }

    // Check if already monitoring
    const { data: existing } = await supabase
      .from('monitored_skills')
      .select('id')
      .eq('user_id', user.id)
      .eq('skill_id', skillRecord.id)
      .single()

    if (existing) {
      return NextResponse.json(
        { detail: 'Already monitoring this skill' },
        { status: 409 }
      )
    }

    // Create monitoring record
    const nextCheck = new Date(Date.now() + check_interval_seconds * 1000)

    const { data: monitor, error } = await supabase
      .from('monitored_skills')
      .insert({
        user_id: user.id,
        skill_id: skillRecord.id,
        status: 'active',
        check_interval_seconds,
        alert_on_critical,
        alert_on_high,
        next_check_at: nextCheck.toISOString(),
      })
      .select('id')
      .single()

    if (error) {
      console.error('Error creating monitor:', error)
      return NextResponse.json(
        { detail: 'Failed to create monitor' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      id: monitor.id,
      skill_id,
      status: 'active',
      check_interval_seconds,
      last_check_at: null,
      next_check_at: nextCheck.toISOString(),
      baseline_trust_score: null,
      findings_detected: 0,
      alerts_sent: 0,
    })
  } catch (error) {
    console.error('Error in monitoring POST:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Delete monitored skill
export async function DELETE(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient()

    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    const url = new URL(request.url)
    const monitorId = url.searchParams.get('id')

    if (!monitorId) {
      return NextResponse.json(
        { detail: 'Monitor ID is required' },
        { status: 400 }
      )
    }

    const { error } = await supabase
      .from('monitored_skills')
      .delete()
      .eq('id', monitorId)
      .eq('user_id', user.id)

    if (error) {
      console.error('Error deleting monitor:', error)
      return NextResponse.json(
        { detail: 'Failed to delete monitor' },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error in monitoring DELETE:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
