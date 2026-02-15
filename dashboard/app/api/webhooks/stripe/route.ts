import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import Stripe from 'stripe'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!
const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY!
const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET!

// Plan mapping from Stripe tier to database plan
const TIER_TO_PLAN: Record<string, string> = {
  pro: 'pro',
  team: 'team',
  enterprise: 'enterprise',
}

// Create Supabase admin client
function getSupabaseAdmin() {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  })
}

// Handle checkout.session.completed event
async function handleCheckoutCompleted(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  session: Stripe.Checkout.Session
) {
  console.log('Processing checkout.session.completed:', session.id)

  const userId = session.metadata?.user_id
  const tier = session.metadata?.tier

  if (!userId || !tier) {
    console.error('Missing user_id or tier in session metadata')
    return
  }

  const plan = TIER_TO_PLAN[tier]
  if (!plan) {
    console.error('Invalid tier:', tier)
    return
  }

  // Update user's plan and subscription ID
  const subscriptionId = session.subscription as string | null

  const { error } = await supabase
    .from('users')
    .update({
      plan,
      stripe_subscription_id: subscriptionId,
      updated_at: new Date().toISOString(),
    })
    .eq('id', userId)

  if (error) {
    console.error('Error updating user plan:', error)
    throw error
  }

  console.log(`Updated user ${userId} to ${plan} plan`)

  // Log the payment event (optional - for audit trail)
  await supabase.from('payment_events').insert({
    user_id: userId,
    event_type: 'checkout.completed',
    stripe_event_id: session.id,
    data: {
      tier,
      plan,
      subscription_id: subscriptionId,
      amount_total: session.amount_total,
      currency: session.currency,
    },
  }).then(({ error }) => {
    if (error) {
      console.error('Error logging payment event:', error)
      // Don't throw - this is optional
    }
  })
}

// Handle invoice.paid event
async function handleInvoicePaid(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  invoice: Stripe.Invoice
) {
  console.log('Processing invoice.paid:', invoice.id)

  const customerId = invoice.customer as string
  const subscriptionId = invoice.subscription as string | null

  if (!customerId) {
    console.error('Missing customer ID in invoice')
    return
  }

  // Find user by Stripe customer ID
  const { data: user, error: fetchError } = await supabase
    .from('users')
    .select('id, plan')
    .eq('stripe_customer_id', customerId)
    .single()

  if (fetchError || !user) {
    console.error('User not found for customer:', customerId)
    return
  }

  // Update subscription ID if not set
  if (subscriptionId && !user.stripe_subscription_id) {
    const { error } = await supabase
      .from('users')
      .update({
        stripe_subscription_id: subscriptionId,
        updated_at: new Date().toISOString(),
      })
      .eq('id', user.id)

    if (error) {
      console.error('Error updating subscription ID:', error)
    }
  }

  // Log the payment
  await supabase.from('payment_events').insert({
    user_id: user.id,
    event_type: 'invoice.paid',
    stripe_event_id: invoice.id,
    data: {
      invoice_number: invoice.number,
      amount_paid: invoice.amount_paid,
      currency: invoice.currency,
      subscription_id: subscriptionId,
    },
  }).then(({ error }) => {
    if (error) {
      console.error('Error logging invoice event:', error)
    }
  })

  console.log(`Processed invoice.paid for user ${user.id}`)
}

// Handle invoice.payment_failed event
async function handleInvoicePaymentFailed(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  invoice: Stripe.Invoice
) {
  console.log('Processing invoice.payment_failed:', invoice.id)

  const customerId = invoice.customer as string

  if (!customerId) {
    console.error('Missing customer ID in invoice')
    return
  }

  // Find user by Stripe customer ID
  const { data: user, error: fetchError } = await supabase
    .from('users')
    .select('id')
    .eq('stripe_customer_id', customerId)
    .single()

  if (fetchError || !user) {
    console.error('User not found for customer:', customerId)
    return
  }

  // Log the failed payment
  await supabase.from('payment_events').insert({
    user_id: user.id,
    event_type: 'invoice.payment_failed',
    stripe_event_id: invoice.id,
    data: {
      invoice_number: invoice.number,
      attempt_count: invoice.attempt_count,
      next_payment_attempt: invoice.next_payment_attempt,
    },
  }).then(({ error }) => {
    if (error) {
      console.error('Error logging failed payment event:', error)
    }
  })

  console.log(`Processed invoice.payment_failed for user ${user.id}`)
}

// Handle customer.subscription.created event
async function handleSubscriptionCreated(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  subscription: Stripe.Subscription
) {
  console.log('Processing customer.subscription.created:', subscription.id)

  const userId = subscription.metadata?.user_id

  if (!userId) {
    console.error('Missing user_id in subscription metadata')
    return
  }

  // Ensure subscription ID is stored
  const { error } = await supabase
    .from('users')
    .update({
      stripe_subscription_id: subscription.id,
      updated_at: new Date().toISOString(),
    })
    .eq('id', userId)

  if (error) {
    console.error('Error updating subscription ID:', error)
    throw error
  }

  console.log(`Updated subscription ID for user ${userId}`)
}

// Handle customer.subscription.updated event
async function handleSubscriptionUpdated(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  subscription: Stripe.Subscription
) {
  console.log('Processing customer.subscription.updated:', subscription.id)

  const customerId = subscription.customer as string

  // Find user by Stripe customer ID
  const { data: user, error: fetchError } = await supabase
    .from('users')
    .select('id, plan')
    .eq('stripe_customer_id', customerId)
    .single()

  if (fetchError || !user) {
    console.error('User not found for customer:', customerId)
    return
  }

  // If subscription is no longer active, downgrade to free
  if (subscription.status !== 'active' && subscription.status !== 'trialing') {
    const { error } = await supabase
      .from('users')
      .update({
        plan: 'free',
        stripe_subscription_id: subscription.id,
        updated_at: new Date().toISOString(),
      })
      .eq('id', user.id)

    if (error) {
      console.error('Error downgrading user:', error)
    } else {
      console.log(`Downgraded user ${user.id} to free plan`)
    }
  } else {
    // Update subscription ID
    const { error } = await supabase
      .from('users')
      .update({
        stripe_subscription_id: subscription.id,
        updated_at: new Date().toISOString(),
      })
      .eq('id', user.id)

    if (error) {
      console.error('Error updating subscription:', error)
    }
  }
}

// Handle customer.subscription.deleted event
async function handleSubscriptionDeleted(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  subscription: Stripe.Subscription
) {
  console.log('Processing customer.subscription.deleted:', subscription.id)

  const customerId = subscription.customer as string

  // Find user by Stripe customer ID
  const { data: user, error: fetchError } = await supabase
    .from('users')
    .select('id')
    .eq('stripe_customer_id', customerId)
    .single()

  if (fetchError || !user) {
    console.error('User not found for customer:', customerId)
    return
  }

  // Downgrade to free plan
  const { error } = await supabase
    .from('users')
    .update({
      plan: 'free',
      stripe_subscription_id: null,
      updated_at: new Date().toISOString(),
    })
    .eq('id', user.id)

  if (error) {
    console.error('Error downgrading user:', error)
    throw error
  }

  // Log the cancellation
  await supabase.from('payment_events').insert({
    user_id: user.id,
    event_type: 'subscription.deleted',
    stripe_event_id: subscription.id,
    data: {
      subscription_id: subscription.id,
      canceled_at: subscription.canceled_at,
    },
  }).then(({ error }) => {
    if (error) {
      console.error('Error logging subscription deletion:', error)
    }
  })

  console.log(`Downgraded user ${user.id} to free plan after subscription deletion`)
}

// Main webhook handler
export async function POST(request: NextRequest) {
  try {
    if (!STRIPE_SECRET_KEY || !STRIPE_WEBHOOK_SECRET) {
      console.error('Stripe webhook not configured')
      return NextResponse.json(
        { error: 'Webhook not configured' },
        { status: 500 }
      )
    }

    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2024-11-20.acacia',
    })

    // Get raw body for signature verification
    const body = await request.text()
    const signature = request.headers.get('stripe-signature')

    if (!signature) {
      console.error('Missing Stripe signature')
      return NextResponse.json(
        { error: 'Missing signature' },
        { status: 400 }
      )
    }

    // Verify webhook signature
    let event: Stripe.Event
    try {
      event = stripe.webhooks.constructEvent(
        body,
        signature,
        STRIPE_WEBHOOK_SECRET
      )
    } catch (err) {
      console.error('Webhook signature verification failed:', err)
      return NextResponse.json(
        { error: 'Invalid signature' },
        { status: 400 }
      )
    }

    console.log('Received Stripe webhook event:', event.type)

    const supabase = getSupabaseAdmin()

    // Handle different event types
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(
          supabase,
          event.data.object as Stripe.Checkout.Session
        )
        break

      case 'invoice.paid':
        await handleInvoicePaid(
          supabase,
          event.data.object as Stripe.Invoice
        )
        break

      case 'invoice.payment_failed':
        await handleInvoicePaymentFailed(
          supabase,
          event.data.object as Stripe.Invoice
        )
        break

      case 'customer.subscription.created':
        await handleSubscriptionCreated(
          supabase,
          event.data.object as Stripe.Subscription
        )
        break

      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(
          supabase,
          event.data.object as Stripe.Subscription
        )
        break

      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(
          supabase,
          event.data.object as Stripe.Subscription
        )
        break

      default:
        console.log('Unhandled event type:', event.type)
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error('Error processing webhook:', error)
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}
