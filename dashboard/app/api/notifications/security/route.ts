import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'
import { sendSecurityAlertEmail } from '@/lib/email'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

/**
 * Send security alert notification for a completed scan
 *
 * POST /api/notifications/security
 * Body: { scanId: string }
 */
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
    const { scanId } = body

    if (!scanId) {
      return NextResponse.json(
        { detail: 'scanId is required' },
        { status: 400 }
      )
    }

    // Get scan details with findings
    const { data: scan, error: scanError } = await supabase
      .from('skill_scans')
      .select(`
        id,
        trust_score,
        risk_level,
        user_id,
        skill:clawhub_skills (
          skill_id,
          name
        )
      `)
      .eq('id', scanId)
      .eq('user_id', user.id)
      .single()

    if (scanError || !scan) {
      return NextResponse.json(
        { detail: 'Scan not found' },
        { status: 404 }
      )
    }

    // Get findings count by severity
    const { data: findings } = await supabase
      .from('skill_findings')
      .select('severity')
      .eq('scan_id', scanId)

    const criticalCount = findings?.filter(f => f.severity === 'critical').length || 0
    const highCount = findings?.filter(f => f.severity === 'high').length || 0

    // Handle skill object (may be array from join)
    const skill = Array.isArray(scan.skill) ? scan.skill[0] : scan.skill

    // Send email notification
    const result = await sendSecurityAlertEmail(user.email || '', {
      skillName: skill?.name || 'Unknown',
      skillId: skill?.skill_id || 'unknown',
      trustScore: scan.trust_score || 0,
      riskLevel: scan.risk_level || 'unknown',
      findingsCount: findings?.length || 0,
      criticalCount,
      highCount,
      scanUrl: `${APP_URL}/scan`,
    })

    if (!result.success) {
      return NextResponse.json(
        { detail: 'Failed to send notification', error: result.error },
        { status: 500 }
      )
    }

    // Log the notification (ignore errors if table doesn't exist)
    supabase.from('notification_logs').insert({
      user_id: user.id,
      type: 'security_alert',
      channel: 'email',
      recipient: user.email,
      subject: `Security Alert: ${skill?.name || 'Unknown'}`,
      status: 'sent',
      metadata: {
        scanId,
        trustScore: scan.trust_score,
        riskLevel: scan.risk_level,
      },
    }).then(() => {}, () => {})

    return NextResponse.json({
      success: true,
      message: 'Security alert notification sent',
    })
  } catch (error) {
    console.error('Error sending security notification:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Get notification preferences
 */
export async function GET() {
  try {
    const supabase = await createSupabaseServerClient()

    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Get notification preferences from user settings
    const { data: preferences } = await supabase
      .from('user_settings')
      .select('notification_preferences')
      .eq('user_id', user.id)
      .single()

    return NextResponse.json({
      preferences: preferences?.notification_preferences || {
        email_budget_alerts: true,
        email_security_alerts: true,
        email_marketing: false,
        alert_thresholds: {
          budget_warning: 80,
          budget_critical: 90,
        },
      },
    })
  } catch (error) {
    console.error('Error fetching notification preferences:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Update notification preferences
 */
export async function PUT(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient()

    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      )
    }

    const preferences = await request.json()

    // Upsert notification preferences
    const { error } = await supabase
      .from('user_settings')
      .upsert({
        user_id: user.id,
        notification_preferences: preferences,
        updated_at: new Date().toISOString(),
      })

    if (error) {
      console.error('Error updating preferences:', error)
      return NextResponse.json(
        { detail: 'Failed to update preferences' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      message: 'Notification preferences updated',
    })
  } catch (error) {
    console.error('Error updating notification preferences:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
