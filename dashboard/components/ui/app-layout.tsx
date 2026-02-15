'use client'

import { Shield, Activity, PieChart, Target, Cpu, ShieldCheck, Key, Settings, Menu, X, Zap, FileText } from 'lucide-react'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { BudgetAlertManager } from '@/components/BudgetAlertManager'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Activity },
  { name: 'Analytics', href: '/analytics', icon: PieChart },
  { name: 'Logs', href: '/logs', icon: FileText },
  { name: 'Budgets', href: '/budgets', icon: Target },
  { name: 'Agents', href: '/agents', icon: Cpu },
  { name: 'Scan', href: '/scan', icon: ShieldCheck },
  { name: 'API Keys', href: '/api-keys', icon: Key },
  { name: 'Settings', href: '/settings', icon: Settings },
]

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Background Effects */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900" />
      <div
        className="fixed inset-0 opacity-30"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2320293a' fill-opacity='0.4'%3E%3Cpath d='M36 34c0-2.209-1.791-4-4-4s-4 1.791-4 4 1.791 4 4 4 4-1.791 4-4zm0-18c0-2.209-1.791-4-4-4s-4 1.791-4 4 1.791 4 4 4 4-1.791 4-4zm18 0c0-2.209-1.791-4-4-4s-4 1.791-4 4 1.791 4 4 4 4-1.791 4-4z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      {/* Content wrapper */}
      <div className="relative">
        {/* Header */}
        <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo */}
              <Link href="/" className="flex items-center gap-3">
                <div className="relative">
                  <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full" />
                  <div className="relative p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/25">
                    <Shield className="text-white" size={22} />
                  </div>
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white tracking-tight">
                    Claw<span className="text-cyan-400">Shell</span>
                  </h1>
                  <p className="text-xs text-slate-500 hidden sm:block">AI Cost Control & Security</p>
                </div>
              </Link>

              {/* Desktop Navigation */}
              <nav className="hidden lg:flex items-center">
                <div className="flex items-center border-b border-slate-800/80 -mb-px">
                  {navigation.map((item) => {
                    const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={cn(
                          'flex items-center gap-2 px-4 py-4 text-sm font-medium border-b-2 -mb-px transition-all duration-200',
                          isActive
                            ? 'text-cyan-400 border-cyan-400'
                            : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600'
                        )}
                      >
                        <item.icon size={16} />
                        <span>{item.name}</span>
                      </Link>
                    )
                  })}
                </div>
              </nav>

              {/* Right section */}
              <div className="flex items-center gap-3">
                {/* Status indicator */}
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <div className="relative">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full" />
                    <div className="absolute inset-0 w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
                  </div>
                  <span className="text-xs text-slate-400 font-medium">Operational</span>
                </div>

                {/* Mobile menu button */}
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="lg:hidden p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white transition-colors"
                >
                  {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
              </div>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="lg:hidden border-t border-slate-800/80 bg-slate-900/95 backdrop-blur-xl">
              <div className="px-4 py-3 space-y-1">
                {navigation.map((item) => {
                  const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all',
                        isActive
                          ? 'text-cyan-400 bg-cyan-500/10'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                      )}
                    >
                      <item.icon size={18} />
                      <span>{item.name}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}
        </header>

        {/* Main content */}
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <Zap size={14} className="text-cyan-400" />
                <span>ClawShell v1.0.0</span>
              </div>
              <div className="flex items-center gap-4">
                <span>Powered by OpenClaw Infrastructure</span>
                <span className="hidden sm:inline">|</span>
                <span className="hidden sm:inline">2026</span>
              </div>
            </div>
          </div>
        </footer>
      </div>

      {/* Budget Alerts */}
      <BudgetAlertManager />
    </div>
  )
}
