'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'
import { type LucideIcon } from 'lucide-react'

// Input variants
const inputVariants = cva(
  'w-full rounded-lg border bg-slate-800/50 text-white placeholder:text-slate-500 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      size: {
        sm: 'px-3 py-1.5 text-sm',
        md: 'px-4 py-2 text-sm',
        lg: 'px-4 py-3 text-base',
      },
      variant: {
        default: 'border-slate-700',
        error: 'border-rose-500/50 focus:ring-rose-500/50 focus:border-rose-500',
        success: 'border-emerald-500/50',
      },
    },
    defaultVariants: {
      size: 'md',
      variant: 'default',
    },
  }
)

interface InputProps extends VariantProps<typeof inputVariants> {
  label?: string
  error?: string
  hint?: string
  icon?: LucideIcon
  iconPosition?: 'left' | 'right'
  className?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps & React.InputHTMLAttributes<HTMLInputElement>>(
  ({ label, error, hint, icon: Icon, iconPosition = 'left', size, variant, className, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="block text-sm font-medium text-slate-300">
            {label}
          </label>
        )}
        <div className="relative">
          {Icon && iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
              <Icon size={16} />
            </div>
          )}
          <input
            ref={ref}
            className={cn(
              inputVariants({ size, variant: error ? 'error' : variant }),
              Icon && iconPosition === 'left' && 'pl-10',
              Icon && iconPosition === 'right' && 'pr-10',
              className
            )}
            {...props}
          />
          {Icon && iconPosition === 'right' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">
              <Icon size={16} />
            </div>
          )}
        </div>
        {error && <p className="text-xs text-rose-400">{error}</p>}
        {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'

// Button variants
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        primary: 'bg-cyan-500 text-white hover:bg-cyan-600 focus:ring-cyan-500',
        secondary: 'bg-slate-700 text-white hover:bg-slate-600 focus:ring-slate-500',
        danger: 'bg-rose-500 text-white hover:bg-rose-600 focus:ring-rose-500',
        ghost: 'text-slate-400 hover:text-white hover:bg-slate-800/50 focus:ring-slate-500',
        outline: 'border border-slate-600 text-slate-300 hover:bg-slate-800/50 hover:border-slate-500 focus:ring-slate-500',
        success: 'bg-emerald-500 text-white hover:bg-emerald-600 focus:ring-emerald-500',
      },
      size: {
        sm: 'px-3 py-1.5 text-sm',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-3 text-base',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

interface ButtonProps extends VariantProps<typeof buttonVariants> {
  icon?: LucideIcon
  iconPosition?: 'left' | 'right'
  loading?: boolean
  className?: string
  children?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps & React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ variant, size, icon: Icon, iconPosition = 'left', loading, className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={props.disabled || loading}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <>
            {Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 14 : 16} />}
            {children}
            {Icon && iconPosition === 'right' && <Icon size={size === 'sm' ? 14 : 16} />}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

// Icon Button
interface IconButtonProps extends Omit<ButtonProps, 'children' | 'icon'> {
  icon: LucideIcon
  'aria-label': string
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps & React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ icon: Icon, variant = 'ghost', size = 'md', className, ...props }, ref) => {
    const sizeClasses = {
      sm: 'p-1.5',
      md: 'p-2',
      lg: 'p-3',
    }

    const buttonSize = size || 'md'

    return (
      <button
        ref={ref}
        className={cn(
          buttonVariants({ variant }),
          sizeClasses[buttonSize],
          className
        )}
        {...props}
      >
        <Icon size={buttonSize === 'sm' ? 14 : buttonSize === 'lg' ? 20 : 16} />
      </button>
    )
  }
)

IconButton.displayName = 'IconButton'

// Select component
interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  options: SelectOption[]
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  label?: string
  error?: string
  className?: string
}

export function Select({ options, value, onChange, placeholder, label, error, className }: SelectProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm font-medium text-slate-300">{label}</label>
      )}
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className={cn(
          'w-full px-4 py-2 rounded-lg border bg-slate-800/50 text-white text-sm',
          'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
          error ? 'border-rose-500/50' : 'border-slate-700',
          className
        )}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  )
}

// Textarea component
interface TextareaProps {
  label?: string
  error?: string
  hint?: string
  rows?: number
  className?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps & React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ label, error, hint, rows = 4, className, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="block text-sm font-medium text-slate-300">{label}</label>
        )}
        <textarea
          ref={ref}
          rows={rows}
          className={cn(
            'w-full px-4 py-2 rounded-lg border bg-slate-800/50 text-white text-sm placeholder:text-slate-500',
            'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
            'resize-none',
            error ? 'border-rose-500/50' : 'border-slate-700',
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-rose-400">{error}</p>}
        {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
    )
  }
)

Textarea.displayName = 'Textarea'
