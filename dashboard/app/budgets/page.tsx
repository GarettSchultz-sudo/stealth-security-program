'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Plus,
  Trash2,
  Edit3,
  X,
  Check,
  Wallet,
  AlertTriangle,
  Clock,
  TrendingUp,
  Globe,
  Cpu,
  Bot,
  Workflow,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardHeader, CardContent, PageHeader, EmptyState, Button, Input, IconButton, Select } from '@/components/ui'

interface Budget {
  id: string
  name: string
  period: 'daily' | 'weekly' | 'monthly'
  limit_usd: number
  current_spend_usd: number
  scope: 'global' | 'agent' | 'model' | 'workflow'
  scope_identifier: string | null
  action_on_breach: 'alert' | 'block' | 'downgrade'
  is_active: boolean
  reset_at: string
  created_at: string
}

const SCOPE_ICONS = {
  global: Globe,
  agent: Bot,
  model: Cpu,
  workflow: Workflow,
}

const PERIOD_LABELS = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
}

const ACTION_LABELS = {
  alert: 'Alert Only',
  block: 'Block Requests',
  downgrade: 'Auto-Downgrade',
}

export default function BudgetsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    period: 'monthly' as 'daily' | 'weekly' | 'monthly',
    limit_usd: '100',
    scope: 'global' as 'global' | 'agent' | 'model' | 'workflow',
    scope_identifier: '',
    action_on_breach: 'alert' as 'alert' | 'block' | 'downgrade',
  })
  const [editForm, setEditForm] = useState<Partial<Budget>>({})

  // Fetch budgets using authenticated endpoint
  const { data: budgets, isLoading } = useQuery<Budget[]>({
    queryKey: ['budgets'],
    queryFn: async () => {
      const response = await fetch('/api/budgets')
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Unauthorized')
        }
        throw new Error('Failed to fetch budgets')
      }
      const data = await response.json()
      return data.budgets || []
    },
  })

  // Create budget mutation
  const createBudget = useMutation({
    mutationFn: async (budgetData: typeof form) => {
      const response = await fetch('/api/budgets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: budgetData.name,
          period: budgetData.period,
          limit_usd: parseFloat(budgetData.limit_usd),
          scope: budgetData.scope,
          scope_identifier: budgetData.scope_identifier || null,
          action_on_breach: budgetData.action_on_breach,
        }),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to create budget')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setShowForm(false)
      setForm({
        name: '',
        period: 'monthly',
        limit_usd: '100',
        scope: 'global',
        scope_identifier: '',
        action_on_breach: 'alert',
      })
      setFormError(null)
    },
    onError: (err: Error) => {
      setFormError(err.message)
    },
  })

  // Update budget mutation
  const updateBudget = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Budget> }) => {
      const response = await fetch(`/api/budgets/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to update budget')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setEditingId(null)
      setEditForm({})
    },
  })

  // Delete budget mutation
  const deleteBudget = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/budgets/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error('Failed to delete budget')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
    },
  })

  const handleCreateBudget = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setFormError('Please enter a name for the budget')
      return
    }
    if (parseFloat(form.limit_usd) <= 0) {
      setFormError('Budget limit must be greater than 0')
      return
    }
    createBudget.mutate(form)
  }

  const handleEditBudget = (budget: Budget) => {
    setEditingId(budget.id)
    setEditForm({
      name: budget.name,
      limit_usd: budget.limit_usd,
      action_on_breach: budget.action_on_breach,
      is_active: budget.is_active,
    })
  }

  const handleSaveEdit = (id: string) => {
    updateBudget.mutate({ id, updates: editForm })
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditForm({})
  }

  const getProgressColor = (current: number, limit: number) => {
    const percent = (current / limit) * 100
    if (percent >= 100) return 'bg-rose-500'
    if (percent >= 80) return 'bg-amber-500'
    return 'bg-emerald-500'
  }

  const getProgressBgColor = (current: number, limit: number) => {
    const percent = (current / limit) * 100
    if (percent >= 100) return 'bg-rose-500/20'
    if (percent >= 80) return 'bg-amber-500/20'
    return 'bg-emerald-500/20'
  }

  const formatResetDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  // Calculate stats
  const totalBudget = budgets?.reduce((sum, b) => sum + b.limit_usd, 0) || 0
  const totalSpend = budgets?.reduce((sum, b) => sum + (b.current_spend_usd || 0), 0) || 0
  const activeBudgets = budgets?.filter((b) => b.is_active).length || 0
  const breachedBudgets = budgets?.filter((b) => b.current_spend_usd >= b.limit_usd).length || 0

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Budgets"
        description="Manage spending limits for your AI agents"
        icon={Wallet}
        iconColor="emerald"
        action={
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setShowForm(true)}
          >
            New Budget
          </Button>
        }
      />

      {/* Create Form */}
      {showForm && (
        <Card variant="default">
          <CardHeader>Create New Budget</CardHeader>
          <CardContent>
            <form onSubmit={handleCreateBudget} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Budget Name"
                  placeholder="e.g., Monthly API Limit"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  error={formError || undefined}
                  hint="Give your budget a recognizable name"
                />
                <Input
                  label="Limit (USD)"
                  type="number"
                  placeholder="100.00"
                  value={form.limit_usd}
                  onChange={(e) => setForm({ ...form, limit_usd: e.target.value })}
                  min="0"
                  step="0.01"
                />
                <Select
                  label="Period"
                  value={form.period}
                  onChange={(value) => setForm({ ...form, period: value as typeof form.period })}
                  options={[
                    { value: 'daily', label: 'Daily' },
                    { value: 'weekly', label: 'Weekly' },
                    { value: 'monthly', label: 'Monthly' },
                  ]}
                />
                <Select
                  label="Scope"
                  value={form.scope}
                  onChange={(value) => setForm({ ...form, scope: value as typeof form.scope })}
                  options={[
                    { value: 'global', label: 'Global (All Agents)' },
                    { value: 'agent', label: 'Specific Agent' },
                    { value: 'model', label: 'Specific Model' },
                    { value: 'workflow', label: 'Specific Workflow' },
                  ]}
                />
                {form.scope !== 'global' && (
                  <Input
                    label="Scope Identifier"
                    placeholder={form.scope === 'agent' ? 'agent-name' : form.scope === 'model' ? 'claude-3-opus' : 'workflow-id'}
                    value={form.scope_identifier}
                    onChange={(e) => setForm({ ...form, scope_identifier: e.target.value })}
                    hint={`The ${form.scope} to apply this budget to`}
                  />
                )}
                <Select
                  label="On Budget Breach"
                  value={form.action_on_breach}
                  onChange={(value) => setForm({ ...form, action_on_breach: value as typeof form.action_on_breach })}
                  options={[
                    { value: 'alert', label: 'Alert Only' },
                    { value: 'block', label: 'Block Requests' },
                    { value: 'downgrade', label: 'Auto-Downgrade' },
                  ]}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  type="submit"
                  variant="primary"
                  loading={createBudget.isPending}
                >
                  Create Budget
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowForm(false)
                    setForm({
                      name: '',
                      period: 'monthly',
                      limit_usd: '100',
                      scope: 'global',
                      scope_identifier: '',
                      action_on_breach: 'alert',
                    })
                    setFormError(null)
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Total Budget</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            ${totalBudget.toFixed(2)}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Current Spend</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            ${totalSpend.toFixed(2)}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Active Budgets</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {activeBudgets}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            {breachedBudgets > 0 ? (
              <AlertTriangle size={14} className="text-rose-400" />
            ) : (
              <Check size={14} className="text-emerald-400" />
            )}
            Status
          </div>
          <div className={cn(
            'text-sm font-medium mt-1',
            breachedBudgets > 0 ? 'text-rose-400' : 'text-emerald-400'
          )}>
            {breachedBudgets > 0 ? `${breachedBudgets} exceeded` : 'All within limits'}
          </div>
        </Card>
      </div>

      {/* Budgets List */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Wallet size={18} className="text-emerald-400" />
            Budget Limits
          </div>
          <span className="text-xs text-slate-500">{budgets?.length || 0} total</span>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500">Loading...</div>
          ) : !budgets || budgets.length === 0 ? (
            <EmptyState
              title="No budgets configured"
              description="Create your first budget to start tracking AI spending"
              action={
                <Button variant="primary" icon={Plus} onClick={() => setShowForm(true)}>
                  Create Budget
                </Button>
              }
            />
          ) : (
            <div className="divide-y divide-slate-800/50">
              {budgets.map((budget) => {
                const ScopeIcon = SCOPE_ICONS[budget.scope]
                const isEditing = editingId === budget.id
                const percentUsed = (budget.current_spend_usd / budget.limit_usd) * 100
                const isBreached = budget.current_spend_usd >= budget.limit_usd

                return (
                  <div
                    key={budget.id}
                    className={cn(
                      'p-4 transition-colors',
                      !budget.is_active && 'opacity-50',
                      isBreached && 'bg-rose-500/5'
                    )}
                  >
                    {isEditing ? (
                      // Edit Mode
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <Input
                            label="Name"
                            value={editForm.name || ''}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                          />
                          <Input
                            label="Limit (USD)"
                            type="number"
                            value={editForm.limit_usd || ''}
                            onChange={(e) => setEditForm({ ...editForm, limit_usd: parseFloat(e.target.value) })}
                            min="0"
                            step="0.01"
                          />
                          <Select
                            label="On Breach"
                            value={editForm.action_on_breach || 'alert'}
                            onChange={(value) => setEditForm({ ...editForm, action_on_breach: value as Budget['action_on_breach'] })}
                            options={[
                              { value: 'alert', label: 'Alert Only' },
                              { value: 'block', label: 'Block Requests' },
                              { value: 'downgrade', label: 'Auto-Downgrade' },
                            ]}
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="primary"
                            icon={Check}
                            onClick={() => handleSaveEdit(budget.id)}
                            loading={updateBudget.isPending}
                          >
                            Save
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={handleCancelEdit}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      // View Mode
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <div className={cn(
                              'p-1.5 rounded-lg',
                              isBreached ? 'bg-rose-500/10' : 'bg-emerald-500/10'
                            )}>
                              <ScopeIcon
                                size={14}
                                className={isBreached ? 'text-rose-400' : 'text-emerald-400'}
                              />
                            </div>
                            <h3 className="font-medium text-white truncate">{budget.name}</h3>
                            {!budget.is_active && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">
                                Inactive
                              </span>
                            )}
                            {isBreached && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400">
                                Exceeded
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-sm text-slate-400">
                            <span>{PERIOD_LABELS[budget.period]}</span>
                            <span className="text-slate-600">•</span>
                            <span className="capitalize">{budget.scope}</span>
                            {budget.scope_identifier && (
                              <>
                                <span className="text-slate-600">•</span>
                                <code className="text-xs bg-slate-800 px-1.5 py-0.5 rounded">
                                  {budget.scope_identifier}
                                </code>
                              </>
                            )}
                          </div>

                          {/* Progress Bar */}
                          <div className="mt-3">
                            <div className="flex justify-between text-sm mb-1.5">
                              <span className="text-slate-400">
                                ${budget.current_spend_usd?.toFixed(2) || '0.00'} spent
                              </span>
                              <span className={cn(
                                'font-medium font-mono',
                                isBreached ? 'text-rose-400' : percentUsed >= 80 ? 'text-amber-400' : 'text-slate-300'
                              )}>
                                {percentUsed.toFixed(0)}%
                              </span>
                            </div>
                            <div className={cn('h-2 rounded-full overflow-hidden', getProgressBgColor(budget.current_spend_usd, budget.limit_usd))}>
                              <div
                                className={cn('h-full rounded-full transition-all', getProgressColor(budget.current_spend_usd, budget.limit_usd))}
                                style={{ width: `${Math.min(100, percentUsed)}%` }}
                              />
                            </div>
                            <div className="flex justify-between text-xs text-slate-500 mt-1.5">
                              <span>Limit: ${budget.limit_usd.toFixed(2)}</span>
                              <span className="flex items-center gap-1">
                                <Clock size={10} />
                                Resets {formatResetDate(budget.reset_at)}
                              </span>
                            </div>
                          </div>

                          {/* Action on Breach */}
                          <div className="mt-2 text-xs text-slate-500">
                            On breach: <span className="text-slate-400">{ACTION_LABELS[budget.action_on_breach]}</span>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1 shrink-0">
                          <IconButton
                            icon={Edit3}
                            aria-label="Edit budget"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditBudget(budget)}
                            className="text-slate-400 hover:text-white hover:bg-slate-700"
                          />
                          <IconButton
                            icon={Trash2}
                            aria-label="Delete budget"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (confirm('Are you sure you want to delete this budget?')) {
                                deleteBudget.mutate(budget.id)
                              }
                            }}
                            className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card variant="default" className="border-cyan-500/20 bg-cyan-500/5">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="text-cyan-400 shrink-0" size={20} />
            <div>
              <h4 className="font-medium text-cyan-400">Budget Tips</h4>
              <ul className="text-sm text-slate-400 mt-2 space-y-1">
                <li>• Set global budgets for overall spending limits across all agents</li>
                <li>• Use model-specific budgets to control costs for expensive models</li>
                <li>• Block mode prevents requests when budget is exceeded</li>
                <li>• Auto-downgrade switches to cheaper models when approaching limits</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
