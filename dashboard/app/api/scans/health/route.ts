import { NextResponse } from 'next/server'

/**
 * Health check endpoint for scanner availability.
 *
 * Checks if the proxy server is available and which scanner tools are installed.
 */
export async function GET() {
  const proxyUrl = process.env.PROXY_URL || process.env.API_URL || 'http://localhost:8000'

  try {
    // Try to connect to proxy health endpoint
    const response = await fetch(`${proxyUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    })

    if (response.ok) {
      const data = await response.json()

      return NextResponse.json({
        status: 'healthy',
        proxy_available: true,
        proxy_url: proxyUrl,
        scanners: data.scanners || {
          nuclei: false,
          trivy: false,
          prowler: false,
        },
        message: 'Proxy server is available',
      })
    }

    return NextResponse.json({
      status: 'degraded',
      proxy_available: false,
      proxy_url: proxyUrl,
      scanners: {
        nuclei: false,
        trivy: false,
        prowler: false,
      },
      message: `Proxy returned status ${response.status}`,
    })
  } catch (error) {
    return NextResponse.json({
      status: 'unavailable',
      proxy_available: false,
      proxy_url: proxyUrl,
      scanners: {
        nuclei: false,
        trivy: false,
        prowler: false,
      },
      message: 'Proxy server is not available. Scans will use simulation mode.',
      error: error instanceof Error ? error.message : 'Unknown error',
    })
  }
}
