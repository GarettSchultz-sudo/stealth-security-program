'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Plus,
  Trash2,
  Copy,
  Check,
  Eye,
  EyeOff,
  Key,
  Shield,
  Clock,
  AlertTriangle,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardHeader, CardContent, PageHeader, EmptyState, Button, Input, IconButton } from '@/components/ui'

interface ApiKey {
  id: string
  name: string
  created_at: string
  last_used_at: string | null
  is_active: boolean
}

export default function ApiKeysPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set())
  const [form, setForm] = useState({ name: '' })
  const [formError, setFormError] = useState<string | null>(null)

  // Fetch API keys using our authenticated endpoint
  const { data: apiKeys, isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const response = await fetch('/api/keys')
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Unauthorized')
        }
        throw new Error('Failed to fetch keys')
      }
      const data = await response.json()
      return data.keys || []
    },
  })

  // Create key mutation
  const createKey = useMutation({
    mutationFn: async (name: string) => {
      const response = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to create key')
      }
      return response.json()
    },
    onSuccess: (data) => {
      setNewKey(data.key)
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setShowForm(false)
      setForm({ name: '' })
      setFormError(null)
    },
    onError: (err: Error) => {
      setFormError(err.message)
    },
  })

  // Delete key mutation
  const deleteKey = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/keys/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error('Failed to delete key')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const toggleIdVisibility = (id: string) => {
    const newVisible = new Set(visibleIds)
    if (newVisible.has(id)) newVisible.delete(id)
    else newVisible.add(id)
    setVisibleIds(newVisible)
  }

  const handleCreateKey = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setFormError('Please enter a name for the API key')
      return
    }
    createKey.mutate(form.name)
  }

  const activeKeys = apiKeys?.filter((k) => k.is_active).length || 0
  const revokedKeys = apiKeys?.filter((k) => !k.is_active).length || 0

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="API Keys"
        description="Manage API keys for your AI agents"
        icon={Key}
        iconColor="cyan"
        action={
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setShowForm(true)}
          >
            Create Key
          </Button>
        }
      />

      {/* New Key Banner */}
      {newKey && (
        <Card variant="elevated" className="border-emerald-500/30 bg-emerald-500/5">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <Key className="text-emerald-400" size={20} />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-emerald-400">New API Key Created</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Copy this key now. You will not be able to see it again.
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <code className="flex-1 bg-slate-900/50 px-3 py-2 rounded-lg border border-slate-700 text-sm font-mono text-white overflow-x-auto">
                    {newKey}
                  </code>
                  <Button
                    variant={copied ? 'success' : 'secondary'}
                    icon={copied ? Check : Copy}
                    onClick={() => copyToClipboard(newKey)}
                    className="shrink-0"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </Button>
                </div>
              </div>
              <IconButton
                icon={X}
                aria-label="Dismiss"
                variant="ghost"
                onClick={() => setNewKey(null)}
                className="text-slate-400 hover:text-white"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Form */}
      {showForm && (
        <Card variant="default">
          <CardHeader>Create New API Key</CardHeader>
          <CardContent>
            <form onSubmit={handleCreateKey} className="space-y-4">
              <Input
                label="Key Name"
                placeholder="e.g., OpenClaw Agent, Cursor IDE"
                value={form.name}
                onChange={(e) => setForm({ name: e.target.value })}
                error={formError || undefined}
                hint="Give your key a recognizable name"
              />
              <div className="flex gap-2">
                <Button
                  type="submit"
                  variant="primary"
                  loading={createKey.isPending}
                >
                  Generate Key
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowForm(false)
                    setForm({ name: '' })
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
          <div className="text-sm text-slate-400">Total Keys</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {apiKeys?.length || 0}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Active</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {activeKeys}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Revoked</div>
          <div className="text-2xl font-bold font-mono text-slate-400 mt-1">
            {revokedKeys}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Shield size={14} />
            Security
          </div>
          <div className="text-sm font-medium text-cyan-400 mt-1">
            Keys are encrypted
          </div>
        </Card>
      </div>

      {/* Keys Table */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key size={18} className="text-cyan-400" />
            API Keys
          </div>
          <span className="text-xs text-slate-500">{apiKeys?.length || 0} total</span>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500">Loading...</div>
          ) : !apiKeys || apiKeys.length === 0 ? (
            <EmptyState
              title="No API keys yet"
              description="Create your first API key to get started"
              action={
                <Button variant="primary" icon={Plus} onClick={() => setShowForm(true)}>
                  Create Key
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Name
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      ID
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Created
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Last Used
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Status
                    </th>
                    <th className="py-3 px-4 border-b border-slate-700/50"></th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr
                      key={key.id}
                      className={cn(
                        'border-b border-slate-800/50 transition-colors',
                        key.is_active ? 'hover:bg-slate-800/30' : 'opacity-60'
                      )}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={cn(
                              'p-1.5 rounded-lg',
                              key.is_active ? 'bg-cyan-500/10' : 'bg-slate-700/50'
                            )}
                          >
                            <Key
                              size={14}
                              className={key.is_active ? 'text-cyan-400' : 'text-slate-500'}
                            />
                          </div>
                          <span className="font-medium text-white">{key.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono text-slate-400">
                            {visibleIds.has(key.id)
                              ? key.id
                              : `${key.id.slice(0, 8)}...${key.id.slice(-4)}`}
                          </code>
                          <button
                            onClick={() => toggleIdVisibility(key.id)}
                            className="text-slate-500 hover:text-slate-300 transition-colors"
                          >
                            {visibleIds.has(key.id) ? (
                              <EyeOff size={14} />
                            ) : (
                              <Eye size={14} />
                            )}
                          </button>
                          <button
                            onClick={() => copyToClipboard(key.id)}
                            className="text-slate-500 hover:text-cyan-400 transition-colors"
                          >
                            <Copy size={14} />
                          </button>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Clock size={12} />
                          {new Date(key.created_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-500">
                        {key.last_used_at
                          ? new Date(key.last_used_at).toLocaleString()
                          : 'Never'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium',
                            key.is_active
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : 'bg-rose-500/10 text-rose-400'
                          )}
                        >
                          {key.is_active ? (
                            <>
                              <Check size={12} />
                              Active
                            </>
                          ) : (
                            <>
                              <X size={12} />
                              Revoked
                            </>
                          )}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <IconButton
                            icon={Trash2}
                            aria-label="Delete key"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (confirm('Are you sure you want to delete this key?')) {
                                deleteKey.mutate(key.id)
                              }
                            }}
                            className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Security Notice */}
      <Card variant="default" className="border-amber-500/20 bg-amber-500/5">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-amber-400 shrink-0" size={20} />
            <div>
              <h4 className="font-medium text-amber-400">Security Best Practices</h4>
              <ul className="text-sm text-slate-400 mt-2 space-y-1">
                <li>• Never share API keys or commit them to version control</li>
                <li>• Use different keys for different environments (dev, staging, prod)</li>
                <li>• Rotate keys periodically and revoke unused keys</li>
                <li>• Monitor key usage for unusual activity</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
