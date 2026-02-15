'use client'

import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'

const cardVariants = cva(
  'rounded-2xl border backdrop-blur-sm transition-all duration-300',
  {
    variants: {
      variant: {
        default: 'bg-slate-900/50 border-slate-800',
        elevated: 'bg-slate-900/80 border-slate-700 shadow-lg',
        ghost: 'bg-transparent border-transparent',
        gradient: 'bg-gradient-to-br from-slate-900/80 to-slate-800/50 border-slate-700/50',
      },
      hover: {
        true: 'hover:border-slate-700 hover:shadow-lg',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      hover: false,
    },
  }
)

interface CardProps extends VariantProps<typeof cardVariants> {
  children: React.ReactNode
  className?: string
}

export function Card({ children, variant, hover, className }: CardProps) {
  return (
    <div className={cn(cardVariants({ variant, hover }), className)}>
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

export function CardHeader({ children, className, action }: CardHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between px-6 py-4 border-b border-slate-800/50', className)}>
      <h3 className="text-lg font-semibold text-white">{children}</h3>
      {action}
    </div>
  )
}

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export function CardContent({ children, className }: CardContentProps) {
  return (
    <div className={cn('p-6', className)}>
      {children}
    </div>
  )
}

// Glass panel for nested content
export function GlassPanel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn(
      'bg-slate-800/30 rounded-xl border border-slate-700/50 p-4',
      className
    )}>
      {children}
    </div>
  )
}

// Section divider with label
export function SectionDivider({ label }: { label?: string }) {
  if (label) {
    return (
      <div className="flex items-center gap-4 my-6">
        <div className="flex-1 h-px bg-slate-800" />
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</span>
        <div className="flex-1 h-px bg-slate-800" />
      </div>
    )
  }
  return <div className="h-px bg-slate-800 my-6" />
}
