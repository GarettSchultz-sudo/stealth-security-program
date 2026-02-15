'use client'

import { cn } from '@/lib/utils'
import { type LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  title: string
  description?: string
  icon?: LucideIcon
  iconColor?: string
  action?: React.ReactNode
  className?: string
  children?: React.ReactNode
}

export function PageHeader({
  title,
  description,
  icon: Icon,
  iconColor = 'cyan',
  action,
  className,
  children,
}: PageHeaderProps) {
  const iconColorClasses: Record<string, string> = {
    cyan: 'text-cyan-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    rose: 'text-rose-400',
    purple: 'text-purple-400',
    blue: 'text-blue-400',
  }

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className={cn('p-2 bg-slate-800/50 rounded-lg', iconColorClasses[iconColor])}>
              <Icon size={24} />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold text-white">{title}</h1>
            {description && (
              <p className="text-sm text-slate-400 mt-0.5">{description}</p>
            )}
          </div>
        </div>
        {action && <div className="flex items-center gap-2">{action}</div>}
      </div>
      {children}
    </div>
  )
}

// Breadcrumb component for navigation context
interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav className={cn('flex items-center gap-2 text-sm', className)}>
      {items.map((item, index) => (
        <span key={index} className="flex items-center gap-2">
          {index > 0 && <span className="text-slate-600">/</span>}
          {item.href ? (
            <a href={item.href} className="text-slate-400 hover:text-cyan-400 transition-colors">
              {item.label}
            </a>
          ) : (
            <span className="text-slate-300">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
