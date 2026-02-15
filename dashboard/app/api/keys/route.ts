import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import crypto from 'crypto'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

// Get current user from session
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

// Generate a new API key
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { name } = body

    // Generate key: acc_<48 random hex chars>
    const keyValue = `acc_${crypto.randomBytes(24).toString('hex')}`

    // Hash the key for storage
    const keyHash = crypto.createHash('sha256').update(keyValue).digest('hex')

    // Create Supabase admin client for insertion
    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: {
        getAll: () => [],
        setAll: () => {},
      },
    })

    // Store in database
    const { data, error } = await supabase
      .from('api_keys')
      .insert({
        user_id: user.id,
        key_hash: keyHash,
        name: name || 'API Key',
      })
      .select()
      .single()

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // Return the plain text key (only time it's shown)
    return NextResponse.json({
      id: data.id,
      name: data.name,
      key: keyValue, // Plain text - only returned once
      created_at: data.created_at,
    })
  } catch (error) {
    console.error('Error creating API key:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// List API keys (without the actual key values)
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: {
        getAll: () => [],
        setAll: () => {},
      },
    })

    const { data, error } = await supabase
      .from('api_keys')
      .select('id, name, created_at, last_used_at, is_active')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    return NextResponse.json({ keys: data })
  } catch (error) {
    console.error('Error listing API keys:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
