'use client'

import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { createClient } from '@supabase/supabase-js'
import type { RealtimeChannel } from '@supabase/supabase-js'

interface RealtimeConfig {
  channel?: string
  table: string
  event?: 'INSERT' | 'UPDATE' | 'DELETE' | '*'
  enabled?: boolean
}

/**
 * Hook to subscribe to Supabase Realtime updates
 * Automatically invalidates React Query cache when data changes
 */
export function useRealtime(config: RealtimeConfig) {
  const {
    channel = `realtime-${config.table}`,
    table,
    event = 'INSERT',
    enabled = true,
  } = config

  const queryClient = useQueryClient()
  const channelRef = useRef<RealtimeChannel | null>(null)
  const supabaseRef = useRef<ReturnType<typeof createClient> | null>(null)

  useEffect(() => {
    if (!enabled) return

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl || !supabaseKey) {
      console.warn('Supabase credentials not configured for realtime')
      return
    }

    // Create Supabase client
    supabaseRef.current = createClient(supabaseUrl, supabaseKey)

    // Create channel
    const realtimeChannel = supabaseRef.current
      .channel(channel)
      .on(
        'postgres_changes',
        {
          event: event,
          schema: 'public',
          table: table,
        },
        (payload) => {
          console.log(`Realtime ${event} on ${table}:`, payload)

          // Invalidate relevant query keys based on the table
          switch (table) {
            case 'request_logs':
              queryClient.invalidateQueries({ queryKey: ['stats'] })
              queryClient.invalidateQueries({ queryKey: ['chart'] })
              queryClient.invalidateQueries({ queryKey: ['models'] })
              queryClient.invalidateQueries({ queryKey: ['logs'] })
              break
            case 'budgets':
              queryClient.invalidateQueries({ queryKey: ['budgets'] })
              break
            case 'api_keys':
              queryClient.invalidateQueries({ queryKey: ['api-keys'] })
              break
            default:
              // Generic invalidation
              queryClient.invalidateQueries({ queryKey: [table] })
          }
        }
      )
      .subscribe((status) => {
        console.log(`Realtime subscription status for ${table}:`, status)
      })

    channelRef.current = realtimeChannel

    // Cleanup
    return () => {
      if (channelRef.current && supabaseRef.current) {
        supabaseRef.current.removeChannel(channelRef.current)
      }
    }
  }, [channel, table, event, enabled, queryClient])

  return {
    isConnected: channelRef.current !== null,
  }
}

/**
 * Hook specifically for request logs realtime updates
 */
export function useRealtimeLogs(enabled = true) {
  return useRealtime({
    table: 'request_logs',
    event: 'INSERT',
    enabled,
  })
}

/**
 * Hook specifically for budgets realtime updates
 */
export function useRealtimeBudgets(enabled = true) {
  return useRealtime({
    table: 'budgets',
    event: '*',
    enabled,
  })
}
