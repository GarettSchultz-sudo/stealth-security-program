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
      // Ensure user exists in public.users table (required for foreign key)
      const { error: userError } = await supabase
        .from('users')
        .upsert({
          id: user.id,
          email: user.email,
        })

      if (userError) {
        console.error('Error creating user:', userError)
        // Continue anyway - user might already exist
      }

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
    simulateScanCompletion(supabase, scan.id, scanProfile, skill_id || target)

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
  profile: ScanProfile,
  target?: string
) {
  // Simulate delay based on scan profile
  const delays = { quick: 2000, standard: 4000, deep: 8000, comprehensive: 15000 }
  const delay = delays[profile] || 4000

  setTimeout(async () => {
    try {
      // Generate deterministic-seeming but varied score based on target hash
      const targetHash = target ? hashCode(target) : Math.random() * 1000
      const randomSeed = (Date.now() + targetHash) % 100

      // Score varies by target and profile depth
      const profileMultipliers = { quick: 0.8, standard: 1.0, deep: 1.1, comprehensive: 1.2 }
      const baseScore = Math.floor((randomSeed * (profileMultipliers[profile] || 1.0)) % 60 + 35)
      const trustScore = Math.min(100, Math.max(0, baseScore))

      // Determine risk level based on score
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

      // Generate mock findings based on risk level
      const findingsCount = riskLevel === 'low' ? Math.floor(Math.random() * 3) :
                           riskLevel === 'medium' ? Math.floor(Math.random() * 5) + 2 :
                           riskLevel === 'high' ? Math.floor(Math.random() * 8) + 5 :
                           Math.floor(Math.random() * 12) + 8

      const filesScanned = Math.floor(Math.random() * 100) + (profile === 'comprehensive' ? 200 : 50)
      const patternsChecked = Math.floor(Math.random() * 500) + (profile === 'deep' ? 300 : 100)

      // Update scan record
      const { error } = await supabase
        .from('skill_scans')
        .update({
          status: 'completed',
          trust_score: trustScore,
          risk_level: riskLevel,
          recommendation,
          scan_duration_ms: delay + Math.floor(Math.random() * 2000),
          files_scanned: filesScanned,
          patterns_checked: patternsChecked,
          completed_at: new Date().toISOString(),
        })
        .eq('id', scanId)

      if (error) {
        console.error('Error updating scan:', error)
      }
    } catch (error) {
      console.error('Error completing scan:', error)
    }
  }, delay)
}

// Simple hash function for deterministic-seeming variety
function hashCode(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return Math.abs(hash)
}
