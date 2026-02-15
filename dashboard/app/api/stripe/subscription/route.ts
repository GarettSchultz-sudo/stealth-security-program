import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import Stripe from 'stripe'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!
const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY!

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

// DELETE /api/stripe/subscription - Cancel subscription
export async function DELETE(request: NextRequest) {
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

    // Get user's subscription ID
    const { data: userData, error: fetchError } = await supabase
      .from('users')
      .select('stripe_subscription_id, stripe_customer_id')
      .eq('id', user.id)
      .single()

    if (fetchError || !userData?.stripe_subscription_id) {
      return NextResponse.json(
        { error: 'No active subscription found' },
        { status: 404 }
      )
    }

    // Initialize Stripe
    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2024-11-20.acacia',
    })

    // Cancel subscription at period end (not immediately)
    const subscription = await stripe.subscriptions.update(
      userData.stripe_subscription_id,
      {
        cancel_at_period_end: true,
      }
    )

    return NextResponse.json({
      status: 'canceled',
      subscription: {
        id: subscription.id,
        status: subscription.status,
        cancel_at_period_end: subscription.cancel_at_period_end,
        current_period_end: subscription.current_period_end,
      },
    })
  } catch (error) {
    console.error('Error canceling subscription:', error)
    return NextResponse.json(
      { error: 'Failed to cancel subscription' },
      { status: 500 }
    )
  }
}

// POST /api/stripe/subscription - Reactivate or update subscription
export async function POST(request: NextRequest) {
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

    const body = await request.json()
    const { action } = body

    // Create Supabase admin client
    const supabase = createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
      cookies: {
        getAll: () => [],
        setAll: () => {},
      },
    })

    // Get user's subscription ID
    const { data: userData, error: fetchError } = await supabase
      .from('users')
      .select('stripe_subscription_id')
      .eq('id', user.id)
      .single()

    if (fetchError) {
      return NextResponse.json(
        { error: 'Failed to fetch user data' },
        { status: 400 }
      )
    }

    // Initialize Stripe
    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2024-11-20.acacia',
    })

    if (action === 'reactivate') {
      // Reactivate a canceled subscription
      if (!userData?.stripe_subscription_id) {
        return NextResponse.json(
          { error: 'No subscription to reactivate' },
          { status: 404 }
        )
      }

      const subscription = await stripe.subscriptions.update(
        userData.stripe_subscription_id,
        {
          cancel_at_period_end: false,
        }
      )

      return NextResponse.json({
        status: 'reactivated',
        subscription: {
          id: subscription.id,
          status: subscription.status,
          cancel_at_period_end: subscription.cancel_at_period_end,
          current_period_end: subscription.current_period_end,
        },
      })
    }

    return NextResponse.json(
      { error: 'Invalid action. Supported: reactivate' },
      { status: 400 }
    )
  } catch (error) {
    console.error('Error updating subscription:', error)
    return NextResponse.json(
      { error: 'Failed to update subscription' },
      { status: 500 }
    )
  }
}

// GET /api/stripe/subscription - Get subscription details
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

    // Get detailed subscription info from Stripe
    let subscriptionDetails = null
    let upcomingInvoice = null

    if (userData?.stripe_subscription_id) {
      try {
        const stripe = new Stripe(STRIPE_SECRET_KEY, {
          apiVersion: '2024-11-20.acacia',
        })

        const subscription = await stripe.subscriptions.retrieve(
          userData.stripe_subscription_id
        )

        subscriptionDetails = {
          id: subscription.id,
          status: subscription.status,
          current_period_start: subscription.current_period_start,
          current_period_end: subscription.current_period_end,
          cancel_at_period_end: subscription.cancel_at_period_end,
          canceled_at: subscription.canceled_at,
          items: subscription.items.data.map((item) => ({
            id: item.id,
            price_id: item.price.id,
            product: item.price.product,
            unit_amount: item.price.unit_amount,
            currency: item.price.currency,
            interval: item.price.recurring?.interval,
          })),
        }

        // Get upcoming invoice
        try {
          upcomingInvoice = await stripe.invoices.retrieveUpcoming({
            customer: userData.stripe_customer_id!,
            subscription: userData.stripe_subscription_id,
          })

          upcomingInvoice = {
            amount_due: upcomingInvoice.amount_due,
            currency: upcomingInvoice.currency,
            next_payment_attempt: upcomingInvoice.next_payment_attempt,
          }
        } catch {
          // No upcoming invoice
          upcomingInvoice = null
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
      upcomingInvoice,
    })
  } catch (error) {
    console.error('Error getting subscription details:', error)
    return NextResponse.json(
      { error: 'Failed to get subscription details' },
      { status: 500 }
    )
  }
}
