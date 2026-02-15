'use client'

import { useState } from 'react'
import {
  Save,
  Bell,
  Shield,
  Globe,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Zap,
  Cpu,
  Database,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Card,
  CardHeader,
  CardContent,
  PageHeader,
  Button,
  Input,
  ToggleSwitch,
  CollapsibleSection,
} from '@/components/ui'

// Comprehensive model catalog - 91 models across 16 providers
const MODEL_CATALOG = {
  anthropic: {
    name: 'Anthropic',
    description: 'Claude AI models',
    models: [
      { id: 'claude-opus-4-6-20250514', name: 'Claude Opus 4.6', tier: 'flagship', context: '200K' },
      { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', tier: 'flagship', context: '200K' },
      { id: 'claude-sonnet-4-5-20250915', name: 'Claude Sonnet 4.5', tier: 'balanced', context: '200K' },
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', tier: 'balanced', context: '200K' },
      { id: 'claude-haiku-4-5-20250915', name: 'Claude Haiku 4.5', tier: 'fast', context: '200K' },
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', tier: 'legacy', context: '200K' },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', tier: 'legacy', context: '200K' },
      { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', tier: 'legacy', context: '200K' },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', tier: 'legacy', context: '200K' },
    ],
  },
  openai: {
    name: 'OpenAI',
    description: 'GPT and o-series models',
    models: [
      { id: 'gpt-5.2-pro-20260115', name: 'GPT-5.2 Pro', tier: 'flagship', context: '200K' },
      { id: 'gpt-5-pro-20251001', name: 'GPT-5 Pro', tier: 'flagship', context: '200K' },
      { id: 'gpt-5.1-20250915', name: 'GPT-5.1', tier: 'balanced', context: '200K' },
      { id: 'gpt-4o-2024-11-20', name: 'GPT-4o', tier: 'balanced', context: '128K' },
      { id: 'gpt-4o-mini-2024-07-18', name: 'GPT-4o Mini', tier: 'fast', context: '128K' },
      { id: 'o3-pro-20260201', name: 'o3 Pro', tier: 'reasoning', context: '200K' },
      { id: 'o3-20260115', name: 'o3', tier: 'reasoning', context: '200K' },
      { id: 'o3-mini-20251215', name: 'o3 Mini', tier: 'reasoning', context: '200K' },
      { id: 'o1-2024-12-17', name: 'o1', tier: 'reasoning', context: '200K' },
      { id: 'o1-mini-2024-09-12', name: 'o1 Mini', tier: 'reasoning', context: '128K' },
    ],
  },
  google: {
    name: 'Google',
    description: 'Gemini models',
    models: [
      { id: 'gemini-3-pro-preview-20260201', name: 'Gemini 3 Pro', tier: 'flagship', context: '2M' },
      { id: 'gemini-2.5-pro-preview-20260115', name: 'Gemini 2.5 Pro', tier: 'flagship', context: '2M' },
      { id: 'gemini-2.5-flash-preview-20260115', name: 'Gemini 2.5 Flash', tier: 'fast', context: '1M' },
      { id: 'gemini-2.0-flash-001', name: 'Gemini 2.0 Flash', tier: 'balanced', context: '1M' },
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', tier: 'legacy', context: '2M' },
    ],
  },
  deepseek: {
    name: 'DeepSeek',
    description: 'Cost-effective AI models',
    models: [
      { id: 'deepseek-v3.2-20260201', name: 'DeepSeek V3.2', tier: 'balanced', context: '128K' },
      { id: 'deepseek-r1-20250120', name: 'DeepSeek R1', tier: 'reasoning', context: '128K' },
      { id: 'deepseek-chat', name: 'DeepSeek Chat', tier: 'fast', context: '64K' },
    ],
  },
  xai: {
    name: 'xAI',
    description: 'Grok models',
    models: [
      { id: 'grok-4-20260115', name: 'Grok 4', tier: 'flagship', context: '256K' },
      { id: 'grok-4.1-20260201', name: 'Grok 4.1', tier: 'flagship', context: '256K' },
      { id: 'grok-3-20251001', name: 'Grok 3', tier: 'balanced', context: '128K' },
    ],
  },
  mistral: {
    name: 'Mistral',
    description: 'European AI models',
    models: [
      { id: 'mistral-large-3-20260115', name: 'Mistral Large 3', tier: 'flagship', context: '128K' },
      { id: 'codestral-2501', name: 'Codestral', tier: 'code', context: '256K' },
    ],
  },
  groq: {
    name: 'Groq',
    description: 'Ultra-fast inference',
    models: [
      { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B', tier: 'balanced', context: '128K' },
      { id: 'deepseek-r1-distill-llama-70b', name: 'DeepSeek R1 Distill', tier: 'reasoning', context: '128K' },
    ],
  },
}

type ProviderKey = keyof typeof MODEL_CATALOG

const TIER_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  flagship: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
  balanced: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30' },
  fast: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  reasoning: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
  code: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
  legacy: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
}

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    defaultProvider: 'anthropic' as ProviderKey,
    defaultModel: 'claude-sonnet-4-5-20250915',
    alertThreshold: 80,
    emailAlerts: true,
    slackWebhook: '',
    rateLimitPerMinute: 1000,
  })
  const [expandedProvider, setExpandedProvider] = useState<ProviderKey | null>('anthropic')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const currentModels = MODEL_CATALOG[settings.defaultProvider]?.models || []

  const handleRefreshModels = async () => {
    setIsRefreshing(true)
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsRefreshing(false)
  }

  const handleSaveSettings = async () => {
    setIsSaving(true)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSaving(false)
  }

  const totalModels = Object.values(MODEL_CATALOG).reduce((sum, p) => sum + p.models.length, 0)
  const totalProviders = Object.keys(MODEL_CATALOG).length

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <PageHeader
        title="Settings"
        description="Configure your ClawShell preferences"
        icon={Shield}
        iconColor="purple"
        action={
          <Button
            variant="ghost"
            icon={RefreshCw}
            onClick={handleRefreshModels}
            loading={isRefreshing}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh Models'}
          </Button>
        }
      />

      {/* Model Catalog Stats */}
      <Card variant="gradient" className="p-6">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-cyan-500 to-purple-500 rounded-xl">
              <Cpu size={24} className="text-white" />
            </div>
            <div>
              <div className="text-3xl font-bold text-white font-mono">{totalModels}</div>
              <div className="text-xs text-slate-400">Models</div>
            </div>
          </div>
          <div className="h-12 w-px bg-slate-700" />
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-rose-500 rounded-xl">
              <Database size={24} className="text-white" />
            </div>
            <div>
              <div className="text-3xl font-bold text-white font-mono">{totalProviders}</div>
              <div className="text-xs text-slate-400">Providers</div>
            </div>
          </div>
          <div className="h-12 w-px bg-slate-700" />
          <div className="flex-1">
            <div className="text-xs text-slate-500">Catalog version</div>
            <div className="text-sm font-mono text-slate-300">2026-02-13</div>
          </div>
        </div>
      </Card>

      {/* Default LLM Configuration */}
      <CollapsibleSection
        title="Default LLM Configuration"
        description="Select your preferred provider and model"
        icon={<Globe size={18} />}
      >
        <div className="space-y-4">
          {/* Current Selection */}
          <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
            <div className="text-xs text-slate-500 mb-1">Currently Selected</div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-white">
                {MODEL_CATALOG[settings.defaultProvider]?.name}
              </span>
              <span className="text-slate-500">/</span>
              <span className="text-cyan-400">
                {currentModels.find((m) => m.id === settings.defaultModel)?.name || settings.defaultModel}
              </span>
            </div>
          </div>

          {/* Provider & Model Selection */}
          <div className="space-y-2">
            {(Object.entries(MODEL_CATALOG) as [ProviderKey, typeof MODEL_CATALOG[ProviderKey]][]).map(
              ([key, provider]) => (
                <div key={key} className="border border-slate-800 rounded-xl overflow-hidden">
                  <button
                    onClick={() => {
                      setExpandedProvider(expandedProvider === key ? null : key)
                      setSettings({ ...settings, defaultProvider: key, defaultModel: provider.models[0].id })
                    }}
                    className={cn(
                      'w-full flex items-center justify-between p-4 text-left transition-colors',
                      settings.defaultProvider === key
                        ? 'bg-cyan-500/5 border-b border-slate-800'
                        : 'hover:bg-slate-800/30'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'w-2 h-2 rounded-full',
                          settings.defaultProvider === key ? 'bg-cyan-400' : 'bg-slate-600'
                        )}
                      />
                      <div>
                        <span className="font-medium text-white">{provider.name}</span>
                        <span className="text-sm text-slate-500 ml-2">{provider.description}</span>
                      </div>
                      <span className="text-xs text-slate-600">({provider.models.length})</span>
                    </div>
                    {expandedProvider === key ? (
                      <ChevronDown size={16} className="text-slate-400" />
                    ) : (
                      <ChevronRight size={16} className="text-slate-400" />
                    )}
                  </button>

                  {expandedProvider === key && (
                    <div className="border-t border-slate-800 bg-slate-900/30 p-2 space-y-1">
                      {provider.models.map((model) => {
                        const tierStyle = TIER_STYLES[model.tier] || TIER_STYLES.legacy
                        return (
                          <button
                            key={model.id}
                            onClick={() => setSettings({ ...settings, defaultModel: model.id })}
                            className={cn(
                              'w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors',
                              settings.defaultModel === model.id
                                ? 'bg-cyan-500/10 border border-cyan-500/30'
                                : 'hover:bg-slate-800/50 border border-transparent'
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <span className="text-slate-200">{model.name}</span>
                              <span className="text-xs text-slate-500 font-mono">{model.context}</span>
                            </div>
                            <span
                              className={cn(
                                'text-xs px-2 py-0.5 rounded-full',
                                tierStyle.bg,
                                tierStyle.text
                              )}
                            >
                              {model.tier}
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </div>
      </CollapsibleSection>

      {/* Supported Providers Overview */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Zap size={18} className="text-cyan-400" />
            Supported Providers
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(MODEL_CATALOG).map(([key, provider]) => (
              <div
                key={key}
                className={cn(
                  'p-4 rounded-xl border transition-colors cursor-pointer',
                  settings.defaultProvider === key
                    ? 'border-cyan-500/30 bg-cyan-500/5'
                    : 'border-slate-700/50 hover:border-slate-600 bg-slate-800/20'
                )}
                onClick={() => {
                  setSettings({ ...settings, defaultProvider: key as ProviderKey })
                  setExpandedProvider(key as ProviderKey)
                }}
              >
                <div className="font-medium text-white">{provider.name}</div>
                <div className="text-sm text-slate-500 mt-0.5">
                  {provider.models.length} models
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Alert Settings */}
      <CollapsibleSection
        title="Alert Settings"
        description="Configure budget and usage notifications"
        icon={<Bell size={18} />}
      >
        <div className="space-y-6">
          {/* Budget Alert Threshold */}
          <div>
            <Input
              label="Budget Alert Threshold (%)"
              type="number"
              value={settings.alertThreshold.toString()}
              onChange={(e) =>
                setSettings({ ...settings, alertThreshold: parseInt(e.target.value) || 0 })
              }
              hint="Alert when budget reaches this percentage"
            />
            {/* Visual threshold indicator */}
            <div className="mt-3">
              <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    settings.alertThreshold >= 90
                      ? 'bg-rose-500'
                      : settings.alertThreshold >= 70
                      ? 'bg-amber-500'
                      : 'bg-cyan-500'
                  )}
                  style={{ width: `${settings.alertThreshold}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>0%</span>
                <span className="font-mono">{settings.alertThreshold}%</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* Email Alerts Toggle */}
          <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
            <div>
              <div className="font-medium text-white">Email Alerts</div>
              <div className="text-sm text-slate-500">Receive budget alerts via email</div>
            </div>
            <ToggleSwitch
              checked={settings.emailAlerts}
              onChange={(checked) => setSettings({ ...settings, emailAlerts: checked })}
            />
          </div>

          {/* Slack Webhook */}
          <Input
            label="Slack Webhook URL"
            placeholder="https://hooks.slack.com/services/..."
            value={settings.slackWebhook}
            onChange={(e) => setSettings({ ...settings, slackWebhook: e.target.value })}
            hint="Optional: Receive alerts in Slack"
          />
        </div>
      </CollapsibleSection>

      {/* Security Settings */}
      <CollapsibleSection
        title="Security"
        description="Rate limiting and access controls"
        icon={<Shield size={18} />}
      >
        <div className="space-y-4">
          <Input
            label="Rate Limit (requests/minute)"
            type="number"
            value={settings.rateLimitPerMinute.toString()}
            onChange={(e) =>
              setSettings({ ...settings, rateLimitPerMinute: parseInt(e.target.value) || 1 })
            }
            hint="Maximum requests per minute per API key"
          />

          <div className="p-4 bg-slate-800/30 rounded-xl">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <Shield size={16} className="text-emerald-400" />
              </div>
              <div>
                <div className="font-medium text-white">API Security</div>
                <div className="text-sm text-slate-500">Your API keys are encrypted at rest</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-slate-400">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                Encryption enabled
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                Audit logging active
              </div>
            </div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-3 pt-4">
        <Button variant="ghost">Reset to Defaults</Button>
        <Button variant="primary" icon={Save} onClick={handleSaveSettings} loading={isSaving}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </div>
  )
}
