'use client'

import { cn } from '@/lib/utils'
import { type LucideIcon, Inbox, Search, FileX, AlertCircle } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4', className)}>
      <div className="p-4 bg-slate-800/50 rounded-2xl mb-4">
        <Icon size={32} className="text-slate-500" />
      </div>
      <h3 className="text-lg font-medium text-slate-300 mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-slate-500 text-center max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// Preset empty states for common use cases
export function EmptySearchState({ query }: { query?: string }) {
  return (
    <EmptyState
      icon={Search}
      title="No results found"
      description={query ? `No items match "${query}"` : 'Try adjusting your search criteria'}
    />
  )
}

export function EmptyDataState({ entityName }: { entityName: string }) {
  return (
    <EmptyState
      icon={FileX}
      title={`No ${entityName} yet`}
      description={`Get started by creating your first ${entityName.toLowerCase()}`}
    />
  )
}

export function EmptyErrorState({ message }: { message?: string }) {
  return (
    <EmptyState
      icon={AlertCircle}
      title="Something went wrong"
      description={message || 'Unable to load data. Please try again.'}
    />
  )
}

// Loading skeleton for lists
export function ListSkeleton({ count = 5, className }: { count?: number; className?: string }) {
  return (
    <div className={cn('space-y-3', className)}>
      {[...Array(count)].map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 p-4 bg-slate-800/30 rounded-xl animate-pulse"
        >
          <div className="w-10 h-10 bg-slate-700/50 rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-slate-700/50 rounded w-1/3" />
            <div className="h-3 bg-slate-700/50 rounded w-1/4" />
          </div>
          <div className="h-6 w-16 bg-slate-700/50 rounded" />
        </div>
      ))}
    </div>
  )
}

// Card skeleton for grid layouts
export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-slate-900/50 border border-slate-800 rounded-2xl p-6 animate-pulse',
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 w-24 bg-slate-700/50 rounded" />
        <div className="h-8 w-8 bg-slate-700/50 rounded-lg" />
      </div>
      <div className="space-y-3">
        <div className="h-3 w-full bg-slate-700/50 rounded" />
        <div className="h-3 w-3/4 bg-slate-700/50 rounded" />
        <div className="h-3 w-1/2 bg-slate-700/50 rounded" />
      </div>
    </div>
  )
}
