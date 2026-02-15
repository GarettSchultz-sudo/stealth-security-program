'use client'

import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon,
  Bell,
  BellOff,
  Shield,
  Clock,
  DollarSign,
  Save,
  RotateCcw,
  Check,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NotificationSettings {
  email_on_critical: boolean
  email_on_high: boolean
  email_on_change: boolean
  slack_webhook_url: string | null
}

interface ScanSettings {
  default_profile: 'quick' | 'standard' | 'deep' | 'comprehensive'
  default_check_interval_seconds: number
  auto_scan_on_add: boolean
}

interface SettingsPanelProps {
  initialSettings?: {
    notifications?: NotificationSettings
    scan?: ScanSettings
  }
  onSave?: (settings: { notifications: NotificationSettings; scan: ScanSettings }) => Promise<void>
  className?: string
}

const defaultSettings = {
  notifications: {
    email_on_critical: true,
    email_on_high: true,
    email_on_change: false,
    slack_webhook_url: null,
  },
  scan: {
    default_profile: 'standard' as const,
    default_check_interval_seconds: 3600,
    auto_scan_on_add: true,
  },
}

const intervalOptions = [
  { value: 1800, label: '30 minutes' },
  { value: 3600, label: '1 hour' },
  { value: 7200, label: '2 hours' },
  { value: 21600, label: '6 hours' },
  { value: 43200, label: '12 hours' },
  { value: 86400, label: '24 hours' },
]

const profileOptions = [
  { value: 'quick', label: 'Quick', description: '1 credit' },
  { value: 'standard', label: 'Standard', description: '2 credits' },
  { value: 'deep', label: 'Deep', description: '5 credits' },
  { value: 'comprehensive', label: 'Comprehensive', description: '10 credits' },
]

export function SettingsPanel({
  initialSettings,
  onSave,
  className,
}: SettingsPanelProps) {
  const [notifications, setNotifications] = useState<NotificationSettings>(
    initialSettings?.notifications ?? defaultSettings.notifications
  )
  const [scan, setScan] = useState<ScanSettings>(
    initialSettings?.scan ?? defaultSettings.scan
  )
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [hasChanges, setHasChanges] = useState(false)

  // Check for changes
  useEffect(() => {
    const initial = initialSettings ?? defaultSettings
    const notifChanged = JSON.stringify(notifications) !== JSON.stringify(initial.notifications)
    const scanChanged = JSON.stringify(scan) !== JSON.stringify(initial.scan)
    setHasChanges(notifChanged || scanChanged)
  }, [notifications, scan, initialSettings])

  const handleSave = async () => {
    if (!onSave) return

    setIsSaving(true)
    setSaveStatus('idle')

    try {
      await onSave({ notifications, scan })
      setSaveStatus('success')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (error) {
      setSaveStatus('error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleReset = () => {
    setNotifications(initialSettings?.notifications ?? defaultSettings.notifications)
    setScan(initialSettings?.scan ?? defaultSettings.scan)
    setSaveStatus('idle')
  }

  const Toggle = ({
    enabled,
    onChange,
    label,
    description,
  }: {
    enabled: boolean
    onChange: (value: boolean) => void
    label: string
    description?: string
  }) => (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <span className="text-sm text-white">{label}</span>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        )}
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors duration-200',
          enabled ? 'bg-cyan-500' : 'bg-slate-700'
        )}
        role="switch"
        aria-checked={enabled}
      >
        <span
          className={cn(
            'absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200',
            enabled ? 'translate-x-6' : 'translate-x-1'
          )}
        />
      </button>
    </div>
  )

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SettingsIcon size={18} className="text-cyan-400" />
          <h3 className="text-sm font-medium text-white">Settings</h3>
        </div>
        {hasChanges && (
          <span className="text-xs text-amber-400">Unsaved changes</span>
        )}
      </div>

      {/* Notification Settings */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-400">
          <Bell size={16} />
          <span className="text-sm font-medium">Notifications</span>
        </div>

        <div className="space-y-4 pl-6">
          <Toggle
            enabled={notifications.email_on_critical}
            onChange={(value) =>
              setNotifications((n) => ({ ...n, email_on_critical: value }))
            }
            label="Email on Critical Findings"
            description="Receive an email when a critical vulnerability is found"
          />

          <Toggle
            enabled={notifications.email_on_high}
            onChange={(value) =>
              setNotifications((n) => ({ ...n, email_on_high: value }))
            }
            label="Email on High Severity"
            description="Receive an email when a high severity issue is found"
          />

          <Toggle
            enabled={notifications.email_on_change}
            onChange={(value) =>
              setNotifications((n) => ({ ...n, email_on_change: value }))
            }
            label="Email on Trust Score Change"
            description="Get notified when monitored skills change significantly"
          />

          {/* Slack Webhook */}
          <div className="pt-2">
            <label className="text-sm text-white block mb-2">
              Slack Webhook URL
            </label>
            <input
              type="text"
              value={notifications.slack_webhook_url ?? ''}
              onChange={(e) =>
                setNotifications((n) => ({
                  ...n,
                  slack_webhook_url: e.target.value || null,
                }))
              }
              placeholder="https://hooks.slack.com/services/..."
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50"
            />
            <p className="text-xs text-slate-500 mt-1">
              Optional: Receive alerts in a Slack channel
            </p>
          </div>
        </div>
      </div>

      {/* Scan Settings */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-400">
          <Shield size={16} />
          <span className="text-sm font-medium">Scan Defaults</span>
        </div>

        <div className="space-y-4 pl-6">
          {/* Default Profile */}
          <div>
            <label className="text-sm text-white block mb-2">
              Default Scan Profile
            </label>
            <div className="grid grid-cols-2 gap-2">
              {profileOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() =>
                    setScan((s) => ({
                      ...s,
                      default_profile: option.value as ScanSettings['default_profile'],
                    }))
                  }
                  className={cn(
                    'flex items-center justify-between p-2.5 rounded-lg border transition-colors',
                    scan.default_profile === option.value
                      ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400'
                      : 'border-slate-700 bg-slate-800/30 text-slate-400 hover:border-slate-600'
                  )}
                >
                  <span className="text-sm">{option.label}</span>
                  <span className="text-xs opacity-75">{option.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Check Interval */}
          <div>
            <label className="text-sm text-white block mb-2">
              Monitoring Check Interval
            </label>
            <select
              value={scan.default_check_interval_seconds}
              onChange={(e) =>
                setScan((s) => ({
                  ...s,
                  default_check_interval_seconds: parseInt(e.target.value),
                }))
              }
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            >
              {intervalOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <Toggle
            enabled={scan.auto_scan_on_add}
            onChange={(value) => setScan((s) => ({ ...s, auto_scan_on_add: value }))}
            label="Auto-scan on Add"
            description="Automatically run a scan when adding a new monitored skill"
          />
        </div>
      </div>

      {/* Save Actions */}
      <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
        <button
          onClick={handleSave}
          disabled={!hasChanges || isSaving || !onSave}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            saveStatus === 'success'
              ? 'bg-emerald-500 text-white'
              : 'bg-cyan-500 text-white hover:bg-cyan-400'
          )}
        >
          {saveStatus === 'success' ? (
            <>
              <Check size={16} />
              Saved
            </>
          ) : saveStatus === 'error' ? (
            <>
              <AlertCircle size={16} />
              Error
            </>
          ) : (
            <>
              <Save size={16} />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </>
          )}
        </button>

        <button
          onClick={handleReset}
          disabled={!hasChanges}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RotateCcw size={16} />
          Reset
        </button>
      </div>
    </div>
  )
}
