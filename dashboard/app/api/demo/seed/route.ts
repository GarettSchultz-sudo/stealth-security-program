import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'
import { seedDemoData } from '@/lib/demo-data'

/**
 * Seed demo data for the current user
 *
 * POST /api/demo/seed
 *
 * This endpoint is called automatically for new users or can be triggered manually
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

    // Check if user already has data
    const { data: existingLogs } = await supabase
      .from('request_logs')
      .select('id')
      .eq('user_id', user.id)
      .limit(1)

    if (existingLogs && existingLogs.length > 0) {
      return NextResponse.json({
        success: false,
        message: 'User already has data. Demo data not seeded.',
      })
    }

    // Seed demo data
    const result = await seedDemoData({
      userId: user.id,
      userEmail: user.email || '',
    })

    if (result.success) {
      return NextResponse.json({
        success: true,
        message: 'Demo data seeded successfully',
        results: result.results,
      })
    } else {
      return NextResponse.json(
        { detail: 'Failed to seed demo data', error: result.error },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('Error in demo seed endpoint:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Check if user has data
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

    // Check for existing data
    const [logsResult, budgetsResult, scansResult] = await Promise.all([
      supabase.from('request_logs').select('id').eq('user_id', user.id).limit(1),
      supabase.from('budgets').select('id').eq('user_id', user.id).limit(1),
      supabase.from('skill_scans').select('id').eq('user_id', user.id).limit(1),
    ])

    const hasData = {
      logs: (logsResult.data?.length || 0) > 0,
      budgets: (budgetsResult.data?.length || 0) > 0,
      scans: (scansResult.data?.length || 0) > 0,
    }

    return NextResponse.json({
      hasData,
      shouldSeedDemo: !hasData.logs && !hasData.budgets && !hasData.scans,
    })
  } catch (error) {
    console.error('Error checking user data:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
