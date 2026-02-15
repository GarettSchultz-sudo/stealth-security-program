'use client'

import { cn } from '@/lib/utils'

interface ToggleSwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  label?: string
  description?: string
  className?: string
}

export function ToggleSwitch({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  label,
  description,
  className,
}: ToggleSwitchProps) {
  const sizeClasses = {
    sm: { track: 'w-8 h-4', thumb: 'w-3 h-3', translate: 'translate-x-4' },
    md: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5' },
    lg: { track: 'w-12 h-6', thumb: 'w-5 h-5', translate: 'translate-x-6' },
  }

  const sizes = sizeClasses[size]

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex items-center rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
          sizes.track,
          checked ? 'bg-cyan-500' : 'bg-slate-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span
          className={cn(
            'inline-block rounded-full bg-white shadow-sm transform transition-transform duration-200',
            sizes.thumb,
            checked ? sizes.translate : 'translate-x-0.5'
          )}
        />
      </button>
      {(label || description) && (
        <div className="flex flex-col">
          {label && <span className="text-sm text-white">{label}</span>}
          {description && <span className="text-xs text-slate-400">{description}</span>}
        </div>
      )}
    </div>
  )
}

// Checkbox with custom styling
interface CheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  className?: string
}

export function Checkbox({ checked, onChange, label, disabled, className }: CheckboxProps) {
  return (
    <label className={cn('flex items-center gap-2 cursor-pointer', disabled && 'opacity-50 cursor-not-allowed', className)}>
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => !disabled && onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
        />
        <div
          className={cn(
            'w-4 h-4 rounded border-2 transition-colors flex items-center justify-center',
            checked ? 'bg-cyan-500 border-cyan-500' : 'border-slate-600 bg-transparent'
          )}
        >
          {checked && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
      </div>
      {label && <span className="text-sm text-slate-300">{label}</span>}
    </label>
  )
}

// Radio button with custom styling
interface RadioOption {
  value: string
  label: string
  description?: string
}

interface RadioGroupProps {
  options: RadioOption[]
  value: string
  onChange: (value: string) => void
  name: string
  disabled?: boolean
  className?: string
}

export function RadioGroup({ options, value, onChange, name, disabled, className }: RadioGroupProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {options.map((option) => (
        <label
          key={option.value}
          className={cn(
            'flex items-start gap-3 cursor-pointer p-3 rounded-lg border transition-colors',
            value === option.value
              ? 'bg-cyan-500/10 border-cyan-500/30'
              : 'bg-slate-800/30 border-slate-700/50 hover:border-slate-600',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <div className="relative mt-0.5">
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(e) => !disabled && onChange(e.target.value)}
              disabled={disabled}
              className="sr-only"
            />
            <div
              className={cn(
                'w-4 h-4 rounded-full border-2 transition-colors flex items-center justify-center',
                value === option.value ? 'border-cyan-500' : 'border-slate-600'
              )}
            >
              {value === option.value && (
                <div className="w-2 h-2 rounded-full bg-cyan-500" />
              )}
            </div>
          </div>
          <div>
            <span className="text-sm text-white">{option.label}</span>
            {option.description && (
              <p className="text-xs text-slate-400 mt-0.5">{option.description}</p>
            )}
          </div>
        </label>
      ))}
    </div>
  )
}
