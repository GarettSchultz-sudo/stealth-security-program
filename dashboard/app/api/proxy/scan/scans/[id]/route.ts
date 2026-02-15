import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

// Get scan details with findings
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createSupabaseServerClient()
    const { id } = await params

    // Get the current user
    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Get scan with skill info
    const { data: scan, error: scanError } = await supabase
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
        error_message,
        skill:clawhub_skills (
          skill_id,
          name,
          author,
          version
        )
      `)
      .eq('id', id)
      .eq('user_id', user.id)
      .single()

    if (scanError || !scan) {
      return NextResponse.json(
        { detail: 'Scan not found' },
        { status: 404 }
      )
    }

    // Get findings for this scan
    const { data: findings } = await supabase
      .from('skill_findings')
      .select('*')
      .eq('scan_id', id)

    // Handle skill - Supabase returns it as array for joins
    const skill = Array.isArray(scan.skill) ? scan.skill[0] : scan.skill

    // Transform response
    const response = {
      id: scan.id,
      skill_id: skill?.skill_id || 'unknown',
      skill_name: skill?.name || 'Unknown',
      skill_author: skill?.author,
      skill_version: skill?.version,
      profile: scan.profile,
      status: scan.status,
      trust_score: scan.trust_score,
      risk_level: scan.risk_level,
      recommendation: scan.recommendation,
      scan_duration_ms: scan.scan_duration_ms,
      files_scanned: scan.files_scanned,
      patterns_checked: scan.patterns_checked,
      created_at: scan.created_at,
      completed_at: scan.completed_at,
      error_message: scan.error_message,
      findings: (findings || []).map((f: Record<string, unknown>) => ({
        id: f.id,
        type: f.finding_type,
        severity: f.severity,
        title: f.title,
        description: f.description,
        file_path: f.file_path,
        line_number: f.line_number,
        code_snippet: f.code_snippet,
        cwe: f.cwe,
        cve: f.cve,
        cvss_score: f.cvss_score,
        remediation: f.remediation,
        reference_urls: f.reference_urls,
        status: f.status,
      })),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching scan details:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
