import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

async function getCurrentUser(request: NextRequest) {
  const cookieStore = await cookies()

  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => cookieStore.set(name, value))
      },
    },
  })

  const { data: { session } } = await supabase.auth.getSession()
  return session?.user
}

// Model downgrade hierarchy with costs
const MODEL_CONFIG: Record<string, { downgrades: string[]; costMultiplier: number }> = {
  'claude-opus-4-6': { downgrades: ['claude-sonnet-4-5-20250929', 'claude-3-5-haiku-20241022'], costMultiplier: 15 },
  'claude-3-opus-20240229': { downgrades: ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307'], costMultiplier: 15 },
  'claude-3-5-sonnet-20241022': { downgrades: ['claude-3-5-haiku-20241022'], costMultiplier: 3 },
  'claude-sonnet-4-5-20250929': { downgrades: ['claude-3-5-haiku-20241022'], costMultiplier: 3 },
  'o1-preview': { downgrades: ['gpt-4o', 'gpt-4o-mini'], costMultiplier: 20 },
  'o1-mini': { downgrades: ['gpt-4o-mini'], costMultiplier: 10 },
  'gpt-4-turbo': { downgrades: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'], costMultiplier: 10 },
  'gpt-4o': { downgrades: ['gpt-4o-mini', 'gpt-3.5-turbo'], costMultiplier: 5 },
  'gpt-4o-mini': { downgrades: ['gpt-3.5-turbo'], costMultiplier: 1.5 },
  'gpt-3.5-turbo': { downgrades: [], costMultiplier: 1 },
  'claude-3-5-haiku-20241022': { downgrades: [], costMultiplier: 1 },
  'claude-3-haiku-20240307': { downgrades: [], costMultiplier: 1 },
}

/**
 * GET /api/models/downgrade - Get available downgrade options
 */
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const currentModel = searchParams.get('model') || 'gpt-4o'

    const config = MODEL_CONFIG[currentModel]
    if (!config) {
      return NextResponse.json({
        currentModel,
        downgradesAvailable: false,
        options: [],
      })
    }

    const options = config.downgrades.map((model, index) => ({
      model,
      tier: index + 1,
      costMultiplier: MODEL_CONFIG[model]?.costMultiplier || 1,
      savingsPercent: Math.round(
        ((config.costMultiplier - (MODEL_CONFIG[model]?.costMultiplier || 1)) /
          config.costMultiplier) *
          100
      ),
    }))

    return NextResponse.json({
      currentModel,
      currentCostMultiplier: config.costMultiplier,
      downgradesAvailable: options.length > 0,
      options,
      recommendation: options[0] || null,
    })
  } catch (error) {
    console.error('Error getting downgrade options:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * POST /api/models/downgrade - Execute model downgrade
 */
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { sessionId, targetModel, preserveContext = true, budgetId } = body

    if (!sessionId) {
      return NextResponse.json({ error: 'sessionId is required' }, { status: 400 })
    }

    // In a real implementation, this would:
    // 1. Find the active session
    // 2. Validate the target model is in the downgrade chain
    // 3. Preserve conversation context
    // 4. Update the session to use the new model
    // 5. Return the new session state

    // For now, return a simulated response
    const currentModel = body.currentModel || 'gpt-4o'
    const config = MODEL_CONFIG[currentModel]

    if (!config || !config.downgrades.includes(targetModel)) {
      return NextResponse.json(
        { error: 'Invalid downgrade target for current model' },
        { status: 400 }
      )
    }

    const currentMultiplier = config.costMultiplier
    const newMultiplier = MODEL_CONFIG[targetModel]?.costMultiplier || 1
    const savingsPercent = Math.round(
      ((currentMultiplier - newMultiplier) / currentMultiplier) * 100
    )

    // Log the downgrade event
    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: { getAll: () => [], setAll: () => {} },
    })

    // Could store this in a budget_events table
    // await supabase.from('budget_events').insert({...})

    return NextResponse.json({
      success: true,
      sessionId,
      downgrade: {
        fromModel: currentModel,
        toModel: targetModel,
        timestamp: new Date().toISOString(),
        contextPreserved: preserveContext,
        savingsPercent,
        estimatedCostMultiplier: newMultiplier,
      },
      message: `Model switched from ${currentModel} to ${targetModel}. Estimated savings: ${savingsPercent}%`,
    })
  } catch (error) {
    console.error('Error executing downgrade:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * DELETE /api/models/downgrade - Cancel/revert a downgrade
 */
export async function DELETE(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get('sessionId')

    if (!sessionId) {
      return NextResponse.json({ error: 'sessionId is required' }, { status: 400 })
    }

    // In a real implementation, revert to original model
    return NextResponse.json({
      success: true,
      message: 'Downgrade cancelled. Session will use original model for next request.',
    })
  } catch (error) {
    console.error('Error cancelling downgrade:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
