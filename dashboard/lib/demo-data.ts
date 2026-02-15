/**
 * Demo data seeder for new users
 *
 * Pre-loads sample data to help new users understand the product value
 */

import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

interface DemoDataConfig {
  userId: string
  userEmail: string
}

/**
 * Seed demo data for a new user
 */
export async function seedDemoData({ userId, userEmail }: DemoDataConfig) {
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  console.log(`Seeding demo data for user ${userId}...`)

  const results = {
    requestLogs: false,
    budget: false,
    scanCredits: false,
    skillScans: false,
  }

  try {
    // 1. Create sample request logs (last 7 days of usage)
    const now = new Date()
    const requestLogs = []

    // Generate realistic usage patterns
    const models = [
      { name: 'gpt-4o', costPerToken: 0.00003 },
      { name: 'gpt-4o-mini', costPerToken: 0.000001 },
      { name: 'claude-3-sonnet', costPerToken: 0.000015 },
      { name: 'claude-3-haiku', costPerToken: 0.0000005 },
    ]

    for (let i = 0; i < 50; i++) {
      const model = models[Math.floor(Math.random() * models.length)]
      const daysAgo = Math.floor(Math.random() * 7)
      const timestamp = new Date(now.getTime() - daysAgo * 86400000 - Math.random() * 86400000)

      const requestTokens = Math.floor(Math.random() * 2000) + 500
      const responseTokens = Math.floor(Math.random() * 3000) + 200
      const cost = (requestTokens + responseTokens) * model.costPerToken * (1 + Math.random() * 0.5)

      requestLogs.push({
        user_id: userId,
        provider: model.name.includes('gpt') ? 'openai' : 'anthropic',
        model: model.name,
        request_tokens: requestTokens,
        response_tokens: responseTokens,
        cost_usd: Math.round(cost * 10000) / 10000,
        latency_ms: Math.floor(Math.random() * 2000) + 200,
        timestamp: timestamp.toISOString(),
        metadata: { workflow: ['chat', 'code', 'analysis'][Math.floor(Math.random() * 3)] },
      })
    }

    const { error: logsError } = await supabase
      .from('request_logs')
      .insert(requestLogs)

    if (logsError) {
      console.error('Error creating request logs:', logsError)
    } else {
      results.requestLogs = true
      console.log(`Created ${requestLogs.length} sample request logs`)
    }

    // 2. Create a demo budget
    const { error: budgetError } = await supabase
      .from('budgets')
      .insert({
        user_id: userId,
        name: 'Monthly AI Budget',
        period: 'monthly',
        limit_usd: 100,
        current_spend_usd: requestLogs.reduce((sum, log) => sum + log.cost_usd, 0),
        scope: 'global',
        action_on_breach: 'alert',
        is_active: true,
      })

    if (budgetError) {
      console.error('Error creating budget:', budgetError)
    } else {
      results.budget = true
      console.log('Created demo budget')
    }

    // 3. Create scan credits for ClawShell Scan
    const periodStart = new Date()
    const periodEnd = new Date()
    periodEnd.setMonth(periodEnd.getMonth() + 1)

    const { error: creditsError } = await supabase
      .from('scan_credits')
      .insert({
        user_id: userId,
        total_credits: 50,
        used_credits: 3,
        period_start: periodStart.toISOString(),
        period_end: periodEnd.toISOString(),
      })

    if (creditsError) {
      console.error('Error creating scan credits:', creditsError)
    } else {
      results.scanCredits = true
      console.log('Created scan credits')
    }

    // 4. Create sample ClawShell Scan skills and scans
    // First create some skills
    const sampleSkills = [
      {
        skill_id: '@openclaw/code-reviewer',
        name: 'Code Reviewer',
        author: 'openclaw',
        version: '1.2.0',
        description: 'Automated code review assistant',
        tags: ['code-quality', 'review'],
      },
      {
        skill_id: '@openclaw/data-analyzer',
        name: 'Data Analyzer',
        author: 'openclaw',
        version: '2.0.1',
        description: 'Analyze and visualize datasets',
        tags: ['data', 'analytics'],
      },
    ]

    const { data: skills, error: skillsError } = await supabase
      .from('clawhub_skills')
      .upsert(sampleSkills, { onConflict: 'skill_id' })
      .select('id, skill_id')

    if (!skillsError && skills) {
      // Create sample scans
      const scanData = [
        {
          skill_id: skills.find(s => s.skill_id === '@openclaw/code-reviewer')?.id,
          trust_score: 92,
          risk_level: 'low',
          status: 'completed',
          recommendation: 'safe',
          profile: 'standard',
        },
        {
          skill_id: skills.find(s => s.skill_id === '@openclaw/data-analyzer')?.id,
          trust_score: 68,
          risk_level: 'medium',
          status: 'completed',
          recommendation: 'caution',
          profile: 'deep',
        },
      ].filter(s => s.skill_id)

      for (const scan of scanData) {
        const completedAt = new Date(now.getTime() - Math.random() * 86400000 * 3)
        const createdAt = new Date(completedAt.getTime() - 5000)

        await supabase
          .from('skill_scans')
          .insert({
            user_id: userId,
            skill_id: scan.skill_id,
            profile: scan.profile,
            status: scan.status,
            trust_score: scan.trust_score,
            risk_level: scan.risk_level,
            recommendation: scan.recommendation,
            scan_duration_ms: Math.floor(Math.random() * 3000) + 1000,
            files_scanned: Math.floor(Math.random() * 50) + 10,
            patterns_checked: Math.floor(Math.random() * 200) + 50,
            created_at: createdAt.toISOString(),
            completed_at: completedAt.toISOString(),
          })
      }

      results.skillScans = true
      console.log('Created sample skill scans')
    }

    console.log('Demo data seeding complete:', results)
    return { success: true, results }
  } catch (error) {
    console.error('Error seeding demo data:', error)
    return { success: false, error: String(error), results }
  }
}

/**
 * API handler for seeding demo data
 */
export async function handleSeedDemoRequest(userId: string, userEmail: string) {
  // Check if user already has data
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  const { data: existingLogs } = await supabase
    .from('request_logs')
    .select('id')
    .eq('user_id', userId)
    .limit(1)

  if (existingLogs && existingLogs.length > 0) {
    return { success: false, message: 'User already has data' }
  }

  return seedDemoData({ userId, userEmail })
}
