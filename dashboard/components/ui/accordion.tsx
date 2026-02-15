'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from './card'

interface AccordionItemProps {
  title: string
  description?: string
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
}

export function AccordionItem({
  title,
  description,
  children,
  defaultOpen = false,
  className,
}: AccordionItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div
      className={cn(
        'border border-slate-800 rounded-xl overflow-hidden transition-colors',
        isOpen && 'border-slate-700',
        className
      )}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
      >
        <div>
          <h3 className="font-medium text-white">{title}</h3>
          {description && (
            <p className="text-sm text-slate-500 mt-0.5">{description}</p>
          )}
        </div>
        <ChevronDown
          size={20}
          className={cn(
            'text-slate-400 transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
        />
      </button>
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="p-4 pt-0 border-t border-slate-800/50">{children}</div>
      </div>
    </div>
  )
}

// Accordion group for multiple items
interface AccordionProps {
  children: React.ReactNode
  className?: string
  allowMultiple?: boolean
}

export function Accordion({ children, className, allowMultiple = true }: AccordionProps) {
  return <div className={cn('space-y-2', className)}>{children}</div>
}

// Collapsible section with header
interface CollapsibleSectionProps {
  title: string
  description?: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
  rightElement?: React.ReactNode
}

export function CollapsibleSection({
  title,
  description,
  icon,
  children,
  className,
  rightElement,
}: CollapsibleSectionProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/50">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2 bg-slate-800/50 rounded-lg text-slate-400">
              {icon}
            </div>
          )}
          <div>
            <h3 className="font-semibold text-white">{title}</h3>
            {description && (
              <p className="text-sm text-slate-500 mt-0.5">{description}</p>
            )}
          </div>
        </div>
        {rightElement}
      </div>
      <div className="p-6">{children}</div>
    </Card>
  )
}
