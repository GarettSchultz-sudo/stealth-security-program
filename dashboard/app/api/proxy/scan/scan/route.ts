import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

// Scan cost mapping
const SCAN_COSTS = {
  quick: 1,
  standard: 2,
  deep: 5,
  comprehensive: 10,
} as const

type ScanProfile = keyof typeof SCAN_COSTS

// Initiate a new scan
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
    const { skill_id, profile = 'standard', target_type, target } = body

    if (!skill_id && !target) {
      return NextResponse.json(
        { detail: 'skill_id or target is required' },
        { status: 400 }
      )
    }

    const scanProfile = profile as ScanProfile
    const scanCost = SCAN_COSTS[scanProfile] || 2

    // Check if user has enough credits
    const now = new Date().toISOString()
    const { data: credits, error: creditsError } = await supabase
      .from('scan_credits')
      .select('*')
      .eq('user_id', user.id)
      .lte('period_start', now)
      .gte('period_end', now)
      .single()

    if (creditsError || !credits) {
      // Create default credits for user if not exists
      const periodStart = new Date()
      const periodEnd = new Date()
      periodEnd.setMonth(periodEnd.getMonth() + 1)

      const { error: insertError } = await supabase
        .from('scan_credits')
        .insert({
          user_id: user.id,
          total_credits: 50,
          used_credits: 0,
          period_start: periodStart.toISOString(),
          period_end: periodEnd.toISOString(),
        })

      if (insertError) {
        console.error('Error creating credits:', insertError)
        return NextResponse.json(
          { detail: 'Failed to initialize credits' },
          { status: 500 }
        )
      }
    } else if ((credits.total_credits - credits.used_credits) < scanCost) {
      return NextResponse.json(
        { detail: 'Insufficient credits for this scan' },
        { status: 402 }
      )
    }

    // Get or create skill record
    let skillRecord
    const { data: existingSkill, error: skillQueryError } = await supabase
      .from('clawhub_skills')
      .select('id')
      .eq('skill_id', skill_id || target)
      .single()

    if (existingSkill) {
      skillRecord = existingSkill
    } else {
      // Create a new skill record
      const { data: newSkill, error: createSkillError } = await supabase
        .from('clawhub_skills')
        .insert({
          skill_id: skill_id || target,
          name: skill_id?.split('/').pop() || target?.split('/').pop() || 'Unknown',
          description: `Scanned via ${target_type || 'url'}`,
        })
        .select('id')
        .single()

      if (createSkillError) {
        console.error('Error creating skill:', createSkillError)
        return NextResponse.json(
          { detail: 'Failed to create skill record' },
          { status: 500 }
        )
      }
      skillRecord = newSkill
    }

    // Create scan record
    const { data: scan, error: scanError } = await supabase
      .from('skill_scans')
      .insert({
        user_id: user.id,
        skill_id: skillRecord.id,
        profile: scanProfile,
        status: 'pending',
      })
      .select('id')
      .single()

    if (scanError) {
      console.error('Error creating scan:', scanError)
      return NextResponse.json(
        { detail: 'Failed to create scan' },
        { status: 500 }
      )
    }

    // Consume credits
    await supabase.rpc('consume_scan_credits', {
      p_user_id: user.id,
      p_profile: scanProfile,
      p_scan_id: scan.id,
    })

    // Simulate scan completion for demo purposes
    // In production, this would be handled by a background worker
    simulateScanCompletion(supabase, scan.id, scanProfile)

    return NextResponse.json({
      scan_id: scan.id,
      status: 'pending',
      message: 'Scan queued successfully',
    }, { status: 202 })
  } catch (error) {
    console.error('Error creating scan:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Simulate scan completion for demo
async function simulateScanCompletion(
  supabase: Awaited<ReturnType<typeof createSupabaseServerClient>>,
  scanId: string,
  profile: ScanProfile
) {
  // Simulate delay based on scan profile
  const delays = { quick: 2000, standard: 4000, deep: 8000, comprehensive: 15000 }
  const delay = delays[profile] || 4000

  setTimeout(async () => {
    try {
      // Generate a random trust score based on profile depth
      const baseScore = Math.floor(Math.random() * 40) + 50 // 50-90 base
      const depthBonus = { quick: 0, standard: 5, deep: 5, comprehensive: 0 }
      const trustScore = Math.min(100, Math.max(0, baseScore + (depthBonus[profile] || 0)))

      // Determine risk level
      let riskLevel: 'low' | 'medium' | 'high' | 'critical'
      let recommendation: 'safe' | 'caution' | 'avoid'
      if (trustScore >= 80) {
        riskLevel = 'low'
        recommendation = 'safe'
      } else if (trustScore >= 60) {
        riskLevel = 'medium'
        recommendation = 'caution'
      } else if (trustScore >= 40) {
        riskLevel = 'high'
        recommendation = 'caution'
      } else {
        riskLevel = 'critical'
        recommendation = 'avoid'
      }

      // Update scan record
      await supabase
        .from('skill_scans')
        .update({
          status: 'completed',
          trust_score: trustScore,
          risk_level: riskLevel,
          recommendation,
          scan_duration_ms: delay,
          files_scanned: Math.floor(Math.random() * 50) + 10,
          patterns_checked: Math.floor(Math.random() * 200) + 50,
          completed_at: new Date().toISOString(),
        })
        .eq('id', scanId)
    } catch (error) {
      console.error('Error completing scan:', error)
    }
  }, delay)
}
