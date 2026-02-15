import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function GET(request: NextRequest) {
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

    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const offset = parseInt(searchParams.get('offset') || '0')
    const status = searchParams.get('status')

    // Build query
    let query = supabase
      .from('skill_scans')
      .select(`
        id,
        profile,
        status,
        trust_score,
        risk_level,
        recommendation,
        scan_duration_ms,
        files_scanned,
        patterns_checked,
        created_at,
        completed_at,
        skill:clawhub_skills (
          skill_id,
          name
        )
      `)
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (status) {
      query = query.eq('status', status)
    }

    const { data: scans, error } = await query

    if (error) {
      console.error('Error fetching scans:', error)
      return NextResponse.json(
        { detail: 'Failed to fetch scans' },
        { status: 500 }
      )
    }

    // Transform to expected format
    const formattedScans = (scans || []).map((scan: any) => ({
      id: scan.id,
      skill_id: scan.skill?.skill_id || 'unknown',
      skill_name: scan.skill?.name || 'Unknown Skill',
      status: scan.status,
      profile: scan.profile,
      trust_score: scan.trust_score,
      risk_level: scan.risk_level,
      recommendation: scan.recommendation,
      scan_duration_ms: scan.scan_duration_ms,
      files_scanned: scan.files_scanned,
      patterns_checked: scan.patterns_checked,
      created_at: scan.created_at,
      completed_at: scan.completed_at,
    }))

    return NextResponse.json({
      scans: formattedScans,
      limit,
      offset,
    })
  } catch (error) {
    console.error('Error in scans endpoint:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
