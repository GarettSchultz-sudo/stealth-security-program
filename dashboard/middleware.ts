import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Refresh session if expired
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const pathname = request.nextUrl.pathname

  // Backwards compatibility: redirect /clawshield to /scan
  if (pathname === '/clawshield' || pathname.startsWith('/clawshield/')) {
    const url = request.nextUrl.clone()
    url.pathname = pathname.replace('/clawshield', '/scan')
    return NextResponse.redirect(url, 301) // Permanent redirect
  }

  // Public routes (no auth required)
  const publicRoutes = ['/', '/login', '/signup', '/demo', '/pricing', '/features', '/docs']
  const isPublicRoute = publicRoutes.some(route => pathname === route || pathname.startsWith(route + '/'))
  const isAuthRoute = pathname.startsWith('/auth/')
  const isMarketingRoute = pathname === '/' || pathname.startsWith('/demo') || pathname.startsWith('/pricing')

  // Allow static files and API
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return supabaseResponse
  }

  // Redirect authenticated users from root to dashboard
  if (pathname === '/' && session) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Allow public and auth routes
  if (isPublicRoute || isAuthRoute) {
    return supabaseResponse
  }

  // Redirect to login if not authenticated
  if (!session) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('next', pathname)
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
}
