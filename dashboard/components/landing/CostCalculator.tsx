'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { TrendingUp, Calculator } from 'lucide-react'
import { Button } from '@/components/ui'

interface CostCalculatorProps {
  className?: string
}

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', multiplier: 1.0 },
  { id: 'anthropic', name: 'Anthropic', multiplier: 1.0 },
  { id: 'google', name: 'Google AI', multiplier: 0.95 },
  { id: 'cohere', name: 'Cohere', multiplier: 0.85 },
  { id: 'mistral', name: 'Mistral', multiplier: 0.80 },
  { id: 'replicate', name: 'Replicate', multiplier: 1.1 },
]

export function CostCalculator({ className = '' }: CostCalculatorProps) {
  const [monthlySpend, setMonthlySpend] = useState(5000)
  const [agentCount, setAgentCount] = useState(10)
  const [selectedProviders, setSelectedProviders] = useState<string[]>(['openai', 'anthropic', 'google', 'cohere'])

  const toggleProvider = (providerId: string) => {
    setSelectedProviders((prev) =>
      prev.includes(providerId)
        ? prev.filter((p) => p !== providerId)
        : [...prev, providerId]
    )
  }

  const calculations = useMemo(() => {
    // Calculate average provider multiplier
    const activeProviders = PROVIDERS.filter((p) => selectedProviders.includes(p.id))
    const avgMultiplier = activeProviders.length > 0
      ? activeProviders.reduce((sum, p) => sum + p.multiplier, 0) / activeProviders.length
      : 1.0

    // Base annual spend
    const annualSpend = monthlySpend * 12 * avgMultiplier

    // Savings calculation:
    // - 15% from smart routing (model downgrades, cost optimization)
    // - 5% from budget enforcement (preventing runaway agents)
    // - Additional savings scale with number of agents (more agents = more potential waste)
    const routingSavings = 0.15
    const enforcementSavings = 0.05
    const agentEfficiencyBonus = Math.min(agentCount * 0.005, 0.10) // Up to 10% bonus based on agent count

    const totalSavingsRate = Math.min(routingSavings + enforcementSavings + agentEfficiencyBonus, 0.35)

    const savingsAmount = annualSpend * totalSavingsRate
    const optimizedSpend = annualSpend - savingsAmount

    return {
      withoutACC: annualSpend,
      withACC: optimizedSpend,
      savings: savingsAmount,
      savingsRate: totalSavingsRate,
    }
  }, [monthlySpend, agentCount, selectedProviders])

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`
    }
    return `$${value.toFixed(0)}`
  }

  return (
    <div className={`rounded-2xl border border-slate-800 bg-slate-900/50 p-8 ${className}`}>
      <div className="grid md:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Monthly AI Spend
            </label>
            <div className="text-3xl font-bold text-white font-mono mb-2">
              {formatCurrency(monthlySpend)}
            </div>
            <input
              type="range"
              min="100"
              max="100000"
              step="100"
              value={monthlySpend}
              onChange={(e) => setMonthlySpend(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>$100</span>
              <span>$100K+</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Number of AI Agents
            </label>
            <input
              type="number"
              value={agentCount}
              onChange={(e) => setAgentCount(Math.max(1, Math.min(1000, Number(e.target.value))))}
              min="1"
              max="1000"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Providers Used
            </label>
            <div className="grid grid-cols-2 gap-2">
              {PROVIDERS.map((provider) => (
                <label
                  key={provider.id}
                  className={`flex items-center gap-2 cursor-pointer p-2 rounded-lg border transition-colors ${
                    selectedProviders.includes(provider.id)
                      ? 'border-indigo-500/50 bg-indigo-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedProviders.includes(provider.id)}
                    onChange={() => toggleProvider(provider.id)}
                    className="rounded border-slate-600 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-slate-300">{provider.name}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="bg-slate-800/50 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calculator className="text-purple-400" size={20} />
            <h4 className="text-lg font-semibold text-white">Estimated Savings</h4>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center py-3 border-b border-slate-700">
              <span className="text-slate-400">Without AgentCostControl</span>
              <span className="text-xl font-bold text-white font-mono">
                {formatCurrency(calculations.withoutACC)}/yr
              </span>
            </div>

            <div className="flex justify-between items-center py-3 border-b border-slate-700">
              <span className="text-slate-400">With AgentCostControl</span>
              <span className="text-xl font-bold text-emerald-400 font-mono">
                {formatCurrency(calculations.withACC)}/yr
              </span>
            </div>

            <div className="flex justify-between items-center py-3">
              <span className="text-slate-300 font-medium">Your Savings</span>
              <div className="text-right">
                <span className="text-2xl font-bold text-emerald-400 font-mono">
                  {formatCurrency(calculations.savings)}/yr
                </span>
                <div className="text-xs text-emerald-400/80">
                  {(calculations.savingsRate * 100).toFixed(0)}% reduction
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <div className="flex items-center gap-2 text-emerald-400 text-sm">
              <TrendingUp size={16} />
              <span>
                Smart routing + budget enforcement ={' '}
                <strong>{(calculations.savingsRate * 100).toFixed(0)}%</strong> average savings
              </span>
            </div>
          </div>

          <Link href="/signup" className="block mt-6">
            <Button
              variant="primary"
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500"
            >
              Start Saving Today
            </Button>
          </Link>

          <p className="text-xs text-slate-500 text-center mt-3">
            No credit card required. Free tier available.
          </p>
        </div>
      </div>
    </div>
  )
}
