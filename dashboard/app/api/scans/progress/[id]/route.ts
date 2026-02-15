import { NextRequest } from 'next/server'
import { Redis } from '@upstash/redis'

// SSE endpoint for real-time scan progress updates
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: scanId } = await params

  // Connect to Upstash Redis for pub/sub
  const redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL!,
    token: process.env.UPSTASH_REDIS_REST_TOKEN!,
  })

  const channel = `scan:${scanId}:progress`

  // Create a ReadableStream for SSE
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder()

      // Send initial connection message
      const connectMessage = `data: ${JSON.stringify({ type: 'connected', scanId })}\n\n`
      controller.enqueue(encoder.encode(connectMessage))

      // Subscribe to Redis channel
      // Note: Upstash Redis doesn't support pub/sub directly in REST API
      // We'll poll the progress key instead
      let lastProgress = 0
      let isComplete = false
      let pollCount = 0
      const maxPolls = 1800 // 30 minutes at 1-second intervals

      const pollInterval = setInterval(async () => {
        try {
          pollCount++

          // Check if scan is complete
          const progressData = await redis.get(`scan:${scanId}:progress`)

          if (progressData) {
            const progress = typeof progressData === 'string'
              ? JSON.parse(progressData)
              : progressData

            // Only send if progress changed
            if (progress.progress !== lastProgress || progress.status === 'completed' || progress.status === 'failed') {
              lastProgress = progress.progress

              const message = `data: ${JSON.stringify({
                type: 'progress',
                scanId,
                ...progress,
                timestamp: new Date().toISOString(),
              })}\n\n`
              controller.enqueue(encoder.encode(message))

              if (progress.status === 'completed' || progress.status === 'failed') {
                isComplete = true
                clearInterval(pollInterval)

                // Send final message
                const completeMessage = `data: ${JSON.stringify({
                  type: 'complete',
                  scanId,
                  status: progress.status,
                })}\n\n`
                controller.enqueue(encoder.encode(completeMessage))
                controller.close()
              }
            }
          }

          // Timeout after max polls
          if (pollCount >= maxPolls && !isComplete) {
            clearInterval(pollInterval)
            const timeoutMessage = `data: ${JSON.stringify({
              type: 'timeout',
              scanId,
              message: 'Scan progress polling timed out',
            })}\n\n`
            controller.enqueue(encoder.encode(timeoutMessage))
            controller.close()
          }
        } catch (error) {
          console.error('Error polling scan progress:', error)
        }
      }, 1000) // Poll every second

      // Handle client disconnect
      const abortHandler = () => {
        clearInterval(pollInterval)
        controller.close()
      }

      request.signal.addEventListener('abort', abortHandler)
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable nginx buffering
    },
  })
}
