import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { seedDemoData } from '@/lib/demo-data'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') ?? '/'

  if (code) {
    const cookieStore = await cookies()

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              )
            } catch {
              // Handle error in middleware/server component
            }
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      // Get the user to seed demo data
      const { data: { user } } = await supabase.auth.getUser()

      if (user) {
        // Ensure user exists in public.users table
        const { error: userError } = await supabase
          .from('users')
          .upsert({
            id: user.id,
            email: user.email,
            plan: 'free',
          })

        // Seed demo data in background (don't await)
        // This runs asynchronously and won't block the redirect
        seedDemoData({
          userId: user.id,
          userEmail: user.email || '',
        }).catch(err => {
          console.error('Failed to seed demo data:', err)
        })
      }

      return NextResponse.redirect(new URL(next, requestUrl.origin))
    }
  }

  // Return to login on error
  return NextResponse.redirect(new URL('/login?error=auth_callback_error', requestUrl.origin))
}
