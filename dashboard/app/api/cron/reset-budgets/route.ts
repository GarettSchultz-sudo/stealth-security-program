import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!
const CRON_SECRET = process.env.CRON_SECRET!

/**
 * Budget Reset Cron Job
 *
 * This endpoint should be called periodically (e.g., every hour) to:
 * 1. Reset budgets that have passed their reset_at date
 * 2. Update reset_at to the next period
 *
 * Called by Vercel Cron Jobs or external scheduler
 *
 * Security: Requires CRON_SECRET header to prevent unauthorized access
 */
export async function GET(request: NextRequest) {
  try {
    // Verify request is from Vercel Cron or has valid CRON_SECRET
    const authHeader = request.headers.get('authorization')
    const vercelCronHeader = request.headers.get('x-vercel-cron')

    // Allow Vercel Cron Jobs or requests with valid CRON_SECRET
    const isVercelCron = vercelCronHeader === 'true' || process.env.VERCEL === '1'
    const providedSecret = authHeader?.replace('Bearer ', '')
    const hasValidSecret = providedSecret && providedSecret === CRON_SECRET

    if (!isVercelCron && !hasValidSecret) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    })

    const now = new Date()
    const nowIso = now.toISOString()

    // Get all active budgets that need reset
    const { data: budgetsToReset, error: fetchError } = await supabase
      .from('budgets')
      .select('id, period, reset_at')
      .eq('is_active', true)
      .lte('reset_at', nowIso)

    if (fetchError) {
      console.error('Error fetching budgets to reset:', fetchError)
      return NextResponse.json({ error: fetchError.message }, { status: 500 })
    }

    if (!budgetsToReset || budgetsToReset.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No budgets to reset',
        resetCount: 0,
      })
    }

    let resetCount = 0
    const errors: string[] = []

    // Reset each budget
    for (const budget of budgetsToReset) {
      // Calculate next reset_at based on period
      const nextResetAt = calculateNextReset(budget.period as 'daily' | 'weekly' | 'monthly')

      // Reset current_spend and update reset_at
      const { error: updateError } = await supabase
        .from('budgets')
        .update({
          current_spend_usd: 0,
          reset_at: nextResetAt.toISOString(),
          updated_at: nowIso,
        })
        .eq('id', budget.id)

      if (updateError) {
        console.error(`Error resetting budget ${budget.id}:`, updateError)
        errors.push(`Budget ${budget.id}: ${updateError.message}`)
      } else {
        resetCount++
      }
    }

    return NextResponse.json({
      success: true,
      message: `Reset ${resetCount} budgets`,
      resetCount,
      totalBudgetsChecked: budgetsToReset.length,
      errors: errors.length > 0 ? errors : undefined,
    })
  } catch (error) {
    console.error('Error in budget reset cron:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * Calculate the next reset date based on the period
 */
function calculateNextReset(period: 'daily' | 'weekly' | 'monthly'): Date {
  const now = new Date()

  switch (period) {
    case 'daily':
      // Next day at 00:00:00 UTC
      const tomorrow = new Date(now)
      tomorrow.setUTCDate(tomorrow.getUTCDate() + 1)
      tomorrow.setUTCHours(0, 0, 0, 0)
      return tomorrow

    case 'weekly':
      // Next Sunday at 00:00:00 UTC (end of week)
      const nextWeek = new Date(now)
      const daysUntilSunday = (7 - nextWeek.getUTCDay()) % 7 || 7
      nextWeek.setUTCDate(nextWeek.getUTCDate() + daysUntilSunday)
      nextWeek.setUTCHours(0, 0, 0, 0)
      return nextWeek

    case 'monthly':
      // First day of next month at 00:00:00 UTC
      const nextMonth = new Date(now)
      nextMonth.setUTCMonth(nextMonth.getUTCMonth() + 1)
      nextMonth.setUTCDate(1)
      nextMonth.setUTCHours(0, 0, 0, 0)
      return nextMonth

    default:
      // Default to daily
      return calculateNextReset('daily')
  }
}
