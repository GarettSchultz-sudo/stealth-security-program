import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import Stripe from 'stripe'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!
const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY!

// Pricing tiers configuration
const PRICING_TIERS = {
  pro: {
    name: 'Pro Plan',
    priceId: process.env.STRIPE_PRO_PRICE_ID!,
    amount: 2900, // $29.00 in cents
    interval: 'month' as const,
  },
  team: {
    name: 'Team Plan',
    priceId: process.env.STRIPE_TEAM_PRICE_ID!,
    amount: 9900, // $99.00 in cents
    interval: 'month' as const,
  },
  enterprise: {
    name: 'Enterprise Plan',
    priceId: process.env.STRIPE_ENTERPRISE_PRICE_ID!,
    amount: 29900, // $299.00 in cents
    interval: 'month' as const,
  },
}

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

// Create or get Stripe customer
async function getOrCreateStripeCustomer(
  supabase: ReturnType<typeof createServerClient>,
  userId: string,
  email: string
): Promise<string> {
  // Check if user already has a Stripe customer ID
  const { data: user, error: fetchError } = await supabase
    .from('users')
    .select('stripe_customer_id')
    .eq('id', userId)
    .single()

  if (fetchError) {
    console.error('Error fetching user:', fetchError)
    throw new Error('Failed to fetch user')
  }

  if (user?.stripe_customer_id) {
    return user.stripe_customer_id
  }

  // Create new Stripe customer
  const stripe = new Stripe(STRIPE_SECRET_KEY, {
    apiVersion: '2024-11-20.acacia',
  })

  const customer = await stripe.customers.create({
    email,
    metadata: {
      supabase_user_id: userId,
    },
  })

  // Store customer ID in database
  const { error: updateError } = await supabase
    .from('users')
    .update({ stripe_customer_id: customer.id })
    .eq('id', userId)

  if (updateError) {
    console.error('Error updating user with Stripe customer ID:', updateError)
    // Continue anyway - we'll still have the customer ID in Stripe
  }

  return customer.id
}

// POST /api/stripe/checkout - Create a checkout session
export async function POST(request: NextRequest) {
  try {
    if (!STRIPE_SECRET_KEY) {
      console.error('STRIPE_SECRET_KEY not configured')
      return NextResponse.json(
        { error: 'Payment system not configured' },
        { status: 500 }
      )
    }

    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { tier, successUrl, cancelUrl } = body

    // Validate tier
    if (!tier || !PRICING_TIERS[tier as keyof typeof PRICING_TIERS]) {
      return NextResponse.json(
        { error: 'Invalid pricing tier. Must be one of: pro, team, enterprise' },
        { status: 400 }
      )
    }

    const selectedTier = PRICING_TIERS[tier as keyof typeof PRICING_TIERS]

    // Create Supabase admin client
    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: {
        getAll: () => [],
        setAll: () => {},
      },
    })

    // Get or create Stripe customer
    const customerId = await getOrCreateStripeCustomer(
      supabase,
      user.id,
      user.email!
    )

    // Initialize Stripe
    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2024-11-20.acacia',
    })

    // Create checkout session
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: selectedTier.priceId
        ? [
            {
              price: selectedTier.priceId,
              quantity: 1,
            },
          ]
        : [
            {
              price_data: {
                currency: 'usd',
                product_data: {
                  name: selectedTier.name,
                  description: `Monthly subscription to ${selectedTier.name}`,
                },
                unit_amount: selectedTier.amount,
                recurring: {
                  interval: selectedTier.interval,
                },
              },
              quantity: 1,
            },
          ],
      success_url: successUrl || `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/settings?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/settings?canceled=true`,
      metadata: {
        user_id: user.id,
        tier: tier,
      },
      subscription_data: {
        metadata: {
          user_id: user.id,
          tier: tier,
        },
      },
    })

    return NextResponse.json({
      sessionId: session.id,
      url: session.url,
    })
  } catch (error) {
    console.error('Error creating checkout session:', error)
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    )
  }
}

// GET /api/stripe/checkout - Get subscription status
export async function GET(request: NextRequest) {
  try {
    if (!STRIPE_SECRET_KEY) {
      return NextResponse.json(
        { error: 'Payment system not configured' },
        { status: 500 }
      )
    }

    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Create Supabase admin client
    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: {
        getAll: () => [],
        setAll: () => {},
      },
    })

    // Get user's subscription info
    const { data: userData, error } = await supabase
      .from('users')
      .select('plan, stripe_customer_id, stripe_subscription_id')
      .eq('id', user.id)
      .single()

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    // If user has a subscription, get more details from Stripe
    let subscriptionDetails = null
    if (userData?.stripe_subscription_id && STRIPE_SECRET_KEY) {
      try {
        const stripe = new Stripe(STRIPE_SECRET_KEY, {
          apiVersion: '2024-11-20.acacia',
        })
        const subscription = await stripe.subscriptions.retrieve(
          userData.stripe_subscription_id
        )
        subscriptionDetails = {
          status: subscription.status,
          current_period_start: subscription.current_period_start,
          current_period_end: subscription.current_period_end,
          cancel_at_period_end: subscription.cancel_at_period_end,
        }
      } catch (stripeError) {
        console.error('Error fetching subscription from Stripe:', stripeError)
        // Continue without Stripe details
      }
    }

    return NextResponse.json({
      plan: userData?.plan || 'free',
      customerId: userData?.stripe_customer_id,
      subscriptionId: userData?.stripe_subscription_id,
      subscription: subscriptionDetails,
    })
  } catch (error) {
    console.error('Error getting subscription status:', error)
    return NextResponse.json(
      { error: 'Failed to get subscription status' },
      { status: 500 }
    )
  }
}
