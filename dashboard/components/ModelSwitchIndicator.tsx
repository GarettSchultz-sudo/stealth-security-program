'use client'

import { useState } from 'react'
import { ArrowDown, ArrowUp, Zap, ChevronDown, Check, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button, Select } from '@/components/ui/input'
import { Card, CardHeader, CardContent } from '@/components/ui/card'

interface ModelOption {
  model: string
  tier: number
  costMultiplier: number
  savingsPercent: number
}

interface ModelSwitchIndicatorProps {
  currentModel: string
  currentCostMultiplier: number
  recommendedModel: string | null
  options: ModelOption[]
  onSwitch: (targetModel: string) => Promise<void>
  isSwitching?: boolean
  className?: string
}

export function ModelSwitchIndicator({
  currentModel,
  currentCostMultiplier,
  recommendedModel,
  options,
  onSwitch,
  isSwitching = false,
  className,
}: ModelSwitchIndicatorProps) {
  const [expanded, setExpanded] = useState(false)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [switchSuccess, setSwitchSuccess] = useState(false)

  const handleSwitch = async (model: string) => {
    await onSwitch(model)
    setSwitchSuccess(true)
    setTimeout(() => setSwitchSuccess(false), 3000)
  }

  const hasDowngrades = options.length > 0
  const savingsAvailable = options[0]?.savingsPercent || 0

  return (
    <Card variant="default" className={cn('', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-amber-400" />
            <span className="text-sm font-medium text-white">Model Selection</span>
          </div>
          {hasDowngrades && (
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
              Save up to {savingsAvailable}%
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {/* Current Model */}
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-xs text-slate-400">Current Model</div>
            <div className="font-mono text-white font-medium">{currentModel}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-400">Cost Tier</div>
            <div className="font-mono text-amber-400">{currentCostMultiplier}x</div>
          </div>
        </div>

        {/* Recommended Downgrade */}
        {recommendedModel && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 mb-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-emerald-400 font-medium">Recommended</div>
                <div className="font-mono text-white">{recommendedModel}</div>
              </div>
              <Button
                variant="success"
                size="sm"
                icon={ArrowDown}
                onClick={() => handleSwitch(recommendedModel)}
                loading={isSwitching}
              >
                Switch
              </Button>
            </div>
            {options.find((o) => o.model === recommendedModel) && (
              <div className="text-xs text-slate-400 mt-2">
                Save {options.find((o) => o.model === recommendedModel)?.savingsPercent}% on this session
              </div>
            )}
          </div>
        )}

        {/* Success Message */}
        {switchSuccess && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 mb-3 flex items-center gap-2">
            <Check size={16} className="text-emerald-400" />
            <span className="text-sm text-emerald-400">Model switched successfully!</span>
          </div>
        )}

        {/* Expandable Options */}
        {hasDowngrades && (
          <>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center justify-between w-full text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              <span>View all downgrade options</span>
              <ChevronDown
                size={16}
                className={cn('transition-transform', expanded && 'rotate-180')}
              />
            </button>

            {expanded && (
              <div className="mt-2 space-y-2">
                {options.map((option) => (
                  <div
                    key={option.model}
                    className={cn(
                      'flex items-center justify-between p-2 rounded-lg border transition-colors',
                      selectedModel === option.model
                        ? 'bg-cyan-500/10 border-cyan-500/30'
                        : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                    )}
                    onClick={() => setSelectedModel(option.model)}
                  >
                    <div>
                      <div className="font-mono text-sm text-white">{option.model}</div>
                      <div className="text-xs text-slate-400">
                        Tier {option.tier} • {option.costMultiplier}x cost
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-emerald-400 font-mono">
                        -{option.savingsPercent}%
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSwitch(option.model)
                        }}
                        loading={isSwitching}
                      >
                        Select
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* No Downgrades Available */}
        {!hasDowngrades && (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Info size={14} />
            <span>You're already using the most cost-effective model</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * CompactModelBadge - Inline model indicator with quick switch
 */
interface CompactModelBadgeProps {
  model: string
  recommendedModel?: string | null
  savingsPercent?: number
  onSwitch?: () => void
  isSwitching?: boolean
}

export function CompactModelBadge({
  model,
  recommendedModel,
  savingsPercent,
  onSwitch,
  isSwitching,
}: CompactModelBadgeProps) {
  const showDowngrade = recommendedModel && savingsPercent && savingsPercent > 0

  return (
    <div className="inline-flex items-center gap-2">
      <span className="px-2 py-1 rounded bg-slate-800 text-xs font-mono text-white">
        {model}
      </span>
      {showDowngrade && onSwitch && (
        <button
          onClick={onSwitch}
          disabled={isSwitching}
          className={cn(
            'inline-flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors',
            'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
          )}
        >
          <ArrowDown size={12} />
          <span>Save {savingsPercent}%</span>
        </button>
      )}
    </div>
  )
}

export default ModelSwitchIndicator
