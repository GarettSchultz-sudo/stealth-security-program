import { NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

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

    // Get current period's credits
    const now = new Date().toISOString()
    const { data: credits, error } = await supabase
      .from('scan_credits')
      .select('*')
      .eq('user_id', user.id)
      .lte('period_start', now)
      .gte('period_end', now)
      .single()

    if (error || !credits) {
      // No credits record found - return default free tier
      return NextResponse.json({
        total_credits: 50,
        used_credits: 0,
        remaining_credits: 50,
        period_end: null,
        scan_costs: {
          quick: 1,
          standard: 2,
          deep: 5,
          comprehensive: 10,
        },
      })
    }

    return NextResponse.json({
      total_credits: credits.total_credits,
      used_credits: credits.used_credits,
      remaining_credits: credits.total_credits - credits.used_credits,
      period_end: credits.period_end,
      scan_costs: {
        quick: credits.quick_scan_cost ?? 1,
        standard: credits.standard_scan_cost ?? 2,
        deep: credits.deep_scan_cost ?? 5,
        comprehensive: credits.comprehensive_scan_cost ?? 10,
      },
    })
  } catch (error) {
    console.error('Error fetching credits:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}
