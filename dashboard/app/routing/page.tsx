'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createClient } from '@supabase/supabase-js'
import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  )
}

export default function RoutingPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    source_model_pattern: '',
    target_model: '',
    priority: 0,
    reason: '',
  })

  const { data: rules, isLoading } = useQuery({
    queryKey: ['routing-rules'],
    queryFn: async () => {
      const supabase = getSupabase()
      const { data } = await supabase.from('routing_rules').select('*').order('priority', { ascending: false })
      return data || []
    },
  })

  const createRule = useMutation({
    mutationFn: async (rule: typeof form) => {
      const supabase = getSupabase()
      const { data } = await supabase.from('routing_rules').insert(rule).select().single()
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['routing-rules'] })
      setShowForm(false)
      setForm({ name: '', source_model_pattern: '', target_model: '', priority: 0, reason: '' })
    },
  })

  const deleteRule = useMutation({
    mutationFn: async (id: string) => {
      const supabase = getSupabase()
      await supabase.from('routing_rules').delete().eq('id', id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['routing-rules'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Routing Rules</h1>
          <p className="text-gray-500 text-sm">Automatically route requests to different models</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
        >
          <Plus size={16} />
          New Rule
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Create Routing Rule</h2>
          <form onSubmit={(e) => { e.preventDefault(); createRule.mutate(form) }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Rule Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="e.g., Budget Downgrade"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Priority</label>
                <input
                  type="number"
                  value={form.priority}
                  onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Source Model Pattern (regex)</label>
                <input
                  type="text"
                  value={form.source_model_pattern}
                  onChange={(e) => setForm({ ...form, source_model_pattern: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="e.g., claude-opus.*"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Target Model</label>
                <input
                  type="text"
                  value={form.target_model}
                  onChange={(e) => setForm({ ...form, target_model: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="e.g., claude-sonnet-4-20250514"
                  required
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium mb-1">Reason</label>
                <input
                  type="text"
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="e.g., Cost optimization"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                Create
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="border px-4 py-2 rounded hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left py-3 px-4 font-medium">Name</th>
              <th className="text-left py-3 px-4 font-medium">Pattern</th>
              <th className="text-left py-3 px-4 font-medium">Target</th>
              <th className="text-center py-3 px-4 font-medium">Priority</th>
              <th className="text-left py-3 px-4 font-medium">Reason</th>
              <th className="text-center py-3 px-4 font-medium">Active</th>
              <th className="py-3 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {rules?.map((rule: any) => (
              <tr key={rule.id} className="border-t hover:bg-gray-50">
                <td className="py-3 px-4 font-medium">{rule.name}</td>
                <td className="py-3 px-4 font-mono text-sm">{rule.source_model_pattern || '*'}</td>
                <td className="py-3 px-4 font-mono text-sm">{rule.target_model}</td>
                <td className="text-center py-3 px-4">{rule.priority}</td>
                <td className="py-3 px-4 text-sm text-gray-500">{rule.reason || '-'}</td>
                <td className="text-center py-3 px-4">
                  <span className={`px-2 py-1 rounded text-xs ${rule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {rule.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <button onClick={() => deleteRule.mutate(rule.id)} className="text-red-500 hover:text-red-700">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
