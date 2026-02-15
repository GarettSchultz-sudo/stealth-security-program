import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { sendBudgetAlertEmail } from '@/lib/email'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!
const CRON_SECRET = process.env.CRON_SECRET!
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

interface BudgetBreaches {
  exceeded: Array<{
    id: string
    name: string
    user_id: string
    current_spend_usd: number
    limit_usd: number
    action_on_breach: string
    period: string
    percent_used: number
  }>
  warning: Array<{
    id: string
    name: string
    user_id: string
    current_spend_usd: number
    limit_usd: number
    percent_used: number
    period: string
  }>
}

/**
 * Budget Breach Check Cron Job
 *
 * This endpoint should be called periodically to:
 * 1. Check for budgets that have exceeded their limit
 * 2. Check for budgets approaching their limit (80%+)
 * 3. Return breach information for alerting
 *
 * In production, this would trigger email/webhook notifications
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

    // Get all active budgets
    const { data: budgets, error: fetchError } = await supabase
      .from('budgets')
      .select('id, name, user_id, current_spend_usd, limit_usd, action_on_breach, period')
      .eq('is_active', true)

    if (fetchError) {
      console.error('Error fetching budgets:', fetchError)
      return NextResponse.json({ error: fetchError.message }, { status: 500 })
    }

    const breaches: BudgetBreaches = {
      exceeded: [],
      warning: [],
    }

    // Check each budget
    for (const budget of budgets || []) {
      const percentUsed = (budget.current_spend_usd / budget.limit_usd) * 100

      if (budget.current_spend_usd >= budget.limit_usd) {
        // Budget exceeded
        breaches.exceeded.push({
          ...budget,
          percent_used: percentUsed,
        })
      } else if (percentUsed >= 80) {
        // Budget approaching limit (80% warning)
        breaches.warning.push({
          ...budget,
          percent_used: percentUsed,
        })
      }
    }

    // Group breaches by user for notification
    const userBreaches: Record<string, BudgetBreaches> = {}

    for (const breach of breaches.exceeded) {
      if (!userBreaches[breach.user_id]) {
        userBreaches[breach.user_id] = { exceeded: [], warning: [] }
      }
      userBreaches[breach.user_id].exceeded.push(breach)
    }

    for (const warning of breaches.warning) {
      if (!userBreaches[warning.user_id]) {
        userBreaches[warning.user_id] = { exceeded: [], warning: [] }
      }
      userBreaches[warning.user_id].warning.push(warning)
    }

    // In production, you would:
    // 1. Fetch user email from auth.users
    // 2. Send email notifications via SendGrid/Resend/Postmark
    // 3. Call webhooks if configured

    // Send email notifications
    const notifications: { userId: string; email: string; sent: boolean }[] = []

    for (const [userId, userBreach] of Object.entries(userBreaches)) {
      // Get user email from auth
      const { data: { user } } = await supabase.auth.admin.getUserById(userId)

      if (!user?.email) continue

      // Send email for each exceeded budget
      for (const exceeded of userBreach.exceeded) {
        const result = await sendBudgetAlertEmail(user.email, {
          budgetName: exceeded.name,
          limit: exceeded.limit_usd,
          currentSpend: exceeded.current_spend_usd,
          percentUsed: (exceeded.current_spend_usd / exceeded.limit_usd) * 100,
          period: exceeded.period,
          actionOnBreach: exceeded.action_on_breach,
          dashboardUrl: `${APP_URL}/budgets`,
        }, 'exceeded')

        notifications.push({ userId, email: user.email, sent: result.success })
      }

      // Send email for critical warnings (90%+)
      for (const warning of userBreach.warning) {
        const type = warning.percent_used >= 90 ? 'critical' : 'warning'

        const result = await sendBudgetAlertEmail(user.email, {
          budgetName: warning.name,
          limit: warning.limit_usd,
          currentSpend: warning.current_spend_usd,
          percentUsed: warning.percent_used,
          period: warning.period,
          actionOnBreach: 'alert',
          dashboardUrl: `${APP_URL}/budgets`,
        }, type)

        notifications.push({ userId, email: user.email, sent: result.success })
      }
    }

    return NextResponse.json({
      success: true,
      timestamp: new Date().toISOString(),
      summary: {
        totalBudgets: budgets?.length || 0,
        exceededCount: breaches.exceeded.length,
        warningCount: breaches.warning.length,
        affectedUsers: Object.keys(userBreaches).length,
        notificationsSent: notifications.filter(n => n.sent).length,
      },
      breaches: breaches.exceeded.length > 0 ? breaches.exceeded : undefined,
      warnings: breaches.warning.length > 0 ? breaches.warning : undefined,
      userBreaches: Object.keys(userBreaches).length > 0 ? userBreaches : undefined,
      notifications: notifications.length > 0 ? notifications : undefined,
    })
  } catch (error) {
    console.error('Error in budget breach check:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
