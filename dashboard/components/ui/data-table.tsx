'use client'

import { cn } from '@/lib/utils'
import { type ReactNode } from 'react'

interface Column<T> {
  key: keyof T | string
  header: string
  align?: 'left' | 'center' | 'right'
  width?: string
  render?: (value: unknown, row: T) => ReactNode
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  className?: string
  emptyMessage?: string
  isLoading?: boolean
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyExtractor,
  className,
  emptyMessage = 'No data available',
  isLoading = false,
}: DataTableProps<T>) {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  }

  if (isLoading) {
    return (
      <div className={cn('overflow-x-auto', className)}>
        <table className="min-w-full">
          <thead>
            <tr className="bg-slate-800/50">
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    'px-4 py-3 text-sm font-medium text-slate-400 border-b border-slate-700/50',
                    alignClasses[col.align || 'left']
                  )}
                  style={{ width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...Array(5)].map((_, i) => (
              <tr key={i} className="border-b border-slate-800/50">
                {columns.map((col) => (
                  <td key={String(col.key)} className="px-4 py-3">
                    <div className="h-4 bg-slate-700/50 rounded animate-pulse" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="min-w-full">
        <thead>
          <tr className="bg-slate-800/50">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={cn(
                  'px-4 py-3 text-sm font-medium text-slate-400 border-b border-slate-700/50',
                  alignClasses[col.align || 'left']
                )}
                style={{ width: col.width }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-slate-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={keyExtractor(row)}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                {columns.map((col) => {
                  const value = col.key.toString().includes('.')
                    ? col.key.toString().split('.').reduce((obj: unknown, key) => {
                        if (obj && typeof obj === 'object') {
                          return (obj as Record<string, unknown>)[key]
                        }
                        return undefined
                      }, row)
                    : row[col.key as keyof T]

                  return (
                    <td
                      key={String(col.key)}
                      className={cn(
                        'px-4 py-3 text-sm',
                        alignClasses[col.align || 'left']
                      )}
                    >
                      {col.render ? col.render(value, row) : (
                        <span className="text-slate-300">
                          {value !== null && value !== undefined ? String(value) : '—'}
                        </span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

// Simple badge for table cells
export function TableBadge({
  children,
  variant = 'default',
  className,
}: {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  className?: string
}) {
  const variantClasses = {
    default: 'bg-slate-700/50 text-slate-300',
    success: 'bg-emerald-500/10 text-emerald-400',
    warning: 'bg-amber-500/10 text-amber-400',
    danger: 'bg-rose-500/10 text-rose-400',
    info: 'bg-cyan-500/10 text-cyan-400',
  }

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
      variantClasses[variant],
      className
    )}>
      {children}
    </span>
  )
}

// Monospace number for financial/numeric data
export function MonoNumber({
  value,
  prefix,
  suffix,
  className,
}: {
  value: number | string
  prefix?: string
  suffix?: string
  className?: string
}) {
  return (
    <span className={cn('font-mono text-slate-200', className)}>
      {prefix}
      {typeof value === 'number' ? value.toLocaleString() : value}
      {suffix}
    </span>
  )
}
