'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItemProps {
  href: string
  label: string
  icon?: LucideIcon
  className?: string
}

export function NavItem({ href, label, icon: Icon, className }: NavItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || (href !== '/' && pathname.startsWith(href))

  return (
    <Link
      href={href}
      className={cn(
        'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200',
        isActive
          ? 'text-cyan-400 bg-cyan-500/10'
          : 'text-slate-400 hover:text-white hover:bg-slate-800/50',
        className
      )}
    >
      {Icon && <Icon size={18} />}
      <span>{label}</span>
    </Link>
  )
}

// Desktop navigation with underline style (for header)
export function NavItemUnderline({ href, label, icon: Icon, className }: NavItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || (href !== '/' && pathname.startsWith(href))

  return (
    <Link
      href={href}
      className={cn(
        'flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-all duration-200',
        isActive
          ? 'text-cyan-400 border-cyan-400'
          : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600',
        className
      )}
    >
      {Icon && <Icon size={16} />}
      <span>{label}</span>
    </Link>
  )
}
