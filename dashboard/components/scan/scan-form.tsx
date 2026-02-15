'use client'

import { useState, useCallback } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import {
  Search,
  Github,
  Globe,
  Container,
  Cloud,
  Database,
  Loader2,
  AlertCircle,
  CheckCircle,
  Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const inputVariants = cva(
  'w-full bg-slate-800/50 border rounded-lg px-4 py-3 text-white placeholder-slate-500 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
  {
    variants: {
      state: {
        default: 'border-slate-700',
        error: 'border-red-500/50 bg-red-500/5',
        success: 'border-emerald-500/50 bg-emerald-500/5',
      },
    },
    defaultVariants: {
      state: 'default',
    },
  }
)

const targetTypeConfig = {
  github: {
    icon: Github,
    label: 'GitHub Repository',
    placeholder: 'https://github.com/owner/repo',
    description: 'Scan repository for vulnerabilities',
    pattern: '^https://github\\.com/[\\w-]+/[\\w.-]+$',
  },
  url: {
    icon: Globe,
    label: 'Web Application',
    placeholder: 'https://example.com',
    description: 'Scan web application for security issues',
    pattern: '^https?://[\\w.-]+(?:\\.[\\w.-]+)+(?::\\d+)?(?:/.*)?$',
  },
  container: {
    icon: Container,
    label: 'Container Image',
    placeholder: 'docker.io/library/nginx:latest',
    description: 'Scan container image for CVEs',
    pattern: '^[\\w.-]+(?:/[\\w.-]+)*(?::[\\w.-]+)?(@sha256:[a-f0-9]+)?$',
  },
  aws: {
    icon: Cloud,
    label: 'AWS Account',
    placeholder: 'arn:aws:iam::123456789012:role/ScanRole',
    description: 'Scan AWS account for misconfigurations',
    pattern: '^arn:aws:iam::\\d{12}:role/[\\w+=,.@-]+$',
  },
  supabase: {
    icon: Database,
    label: 'Supabase Project',
    placeholder: 'https://yourproject.supabase.co',
    description: 'Scan Supabase project security',
    pattern: '^https://[\\w-]+\\.supabase\\.co$',
  },
}

type TargetType = keyof typeof targetTypeConfig

const scanProfiles = [
  { id: 'quick', label: 'Quick', cost: 1, description: 'Basic pattern checks' },
  { id: 'standard', label: 'Standard', cost: 2, description: 'Recommended for most uses' },
  { id: 'deep', label: 'Deep', cost: 5, description: 'Full SAST analysis' },
  { id: 'comprehensive', label: 'Comprehensive', cost: 10, description: 'Includes external API checks' },
]

interface ScanFormProps {
  onSubmit: (data: ScanFormData) => Promise<void>
  credits: number
  isSubmitting?: boolean
  className?: string
}

export interface ScanFormData {
  target_type: TargetType
  target: string
  profile: 'quick' | 'standard' | 'deep' | 'comprehensive'
}

export function ScanForm({ onSubmit, credits, isSubmitting = false, className }: ScanFormProps) {
  const [targetType, setTargetType] = useState<TargetType>('github')
  const [target, setTarget] = useState('')
  const [profile, setProfile] = useState<'quick' | 'standard' | 'deep' | 'comprehensive'>('standard')
  const [validationState, setValidationState] = useState<'default' | 'error' | 'success'>('default')
  const [errorMessage, setErrorMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const config = targetTypeConfig[targetType]
  const Icon = config.icon
  const selectedProfile = scanProfiles.find(p => p.id === profile)!
  const canAfford = credits >= selectedProfile.cost

  const validateTarget = useCallback((value: string): boolean => {
    if (!value.trim()) {
      setValidationState('default')
      setErrorMessage('')
      return false
    }

    const regex = new RegExp(config.pattern)
    const isValid = regex.test(value)

    if (isValid) {
      setValidationState('success')
      setErrorMessage('')
    } else {
      setValidationState('error')
      setErrorMessage(`Invalid ${config.label.toLowerCase()} format`)
    }

    return isValid
  }, [config])

  const handleTargetChange = (value: string) => {
    setTarget(value)
    validateTarget(value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const isValid = validateTarget(target)
    if (!isValid) {
      return
    }

    if (!canAfford) {
      setValidationState('error')
      setErrorMessage('Insufficient credits for this scan profile')
      return
    }

    await onSubmit({
      target_type: targetType,
      target: target.trim(),
      profile,
    })
  }

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-6', className)}>
      {/* Target Type Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-3">
          Target Type
        </label>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {(Object.entries(targetTypeConfig) as [TargetType, typeof config][]).map(([type, cfg]) => {
            const TypeIcon = cfg.icon
            return (
              <button
                key={type}
                type="button"
                onClick={() => {
                  setTargetType(type)
                  setTarget('')
                  setValidationState('default')
                  setErrorMessage('')
                }}
                className={cn(
                  'flex flex-col items-center gap-2 p-3 rounded-lg border transition-all duration-200',
                  'hover:bg-slate-800/50',
                  targetType === type
                    ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400'
                    : 'border-slate-700 bg-slate-800/30 text-slate-400 hover:border-slate-600'
                )}
              >
                <TypeIcon size={20} />
                <span className="text-xs font-medium">{cfg.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Target Input */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Target
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Icon size={18} className={cn(
              'transition-colors',
              validationState === 'error' ? 'text-red-400' :
              validationState === 'success' ? 'text-emerald-400' :
              isFocused ? 'text-cyan-400' : 'text-slate-500'
            )} />
          </div>
          <input
            type="text"
            value={target}
            onChange={(e) => handleTargetChange(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={config.placeholder}
            className={cn(inputVariants({ state: validationState }), 'pl-10')}
            aria-invalid={validationState === 'error'}
            aria-describedby={errorMessage ? 'target-error' : undefined}
          />
          {validationState === 'success' && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <CheckCircle size={18} className="text-emerald-400" />
            </div>
          )}
          {validationState === 'error' && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <AlertCircle size={18} className="text-red-400" />
            </div>
          )}
        </div>
        {errorMessage && (
          <p id="target-error" className="mt-2 text-sm text-red-400 flex items-center gap-1">
            <AlertCircle size={14} />
            {errorMessage}
          </p>
        )}
        {!errorMessage && (
          <p className="mt-2 text-xs text-slate-500">{config.description}</p>
        )}
      </div>

      {/* Scan Profile */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-3">
          Scan Profile
        </label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {scanProfiles.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setProfile(p.id as typeof profile)}
              disabled={credits < p.cost}
              className={cn(
                'flex flex-col items-center p-3 rounded-lg border transition-all duration-200',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                profile === p.id
                  ? 'border-cyan-500/50 bg-cyan-500/10'
                  : 'border-slate-700 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50'
              )}
            >
              <span className={cn(
                'text-sm font-medium',
                profile === p.id ? 'text-cyan-400' : 'text-slate-300'
              )}>
                {p.label}
              </span>
              <span className="text-xs text-slate-500 mt-1">{p.cost} credits</span>
              <span className="text-[10px] text-slate-600 mt-0.5 text-center">
                {p.description}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-2 text-sm">
          <Shield size={16} className={canAfford ? 'text-emerald-400' : 'text-red-400'} />
          <span className={canAfford ? 'text-slate-400' : 'text-red-400'}>
            {canAfford
              ? `${credits} credits available`
              : `Need ${selectedProfile.cost - credits} more credits`}
          </span>
        </div>
        <button
          type="submit"
          disabled={isSubmitting || !target.trim() || validationState === 'error' || !canAfford}
          className={cn(
            'flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-all duration-200',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400',
            'text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40'
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Scanning...
            </>
          ) : (
            <>
              <Search size={18} />
              Start Scan
            </>
          )}
        </button>
      </div>
    </form>
  )
}
