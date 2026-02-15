/**
 * Tests for CostCalculator component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CostCalculator } from '@/components/landing/CostCalculator'

// Mock Next.js Link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

describe('CostCalculator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render with default values', () => {
    render(<CostCalculator />)

    // Check default monthly spend ($5,000)
    expect(screen.getByText('$5K')).toBeInTheDocument()

    // Check agent count input
    const agentInput = screen.getByRole('spinbutton')
    expect(agentInput).toHaveValue(10)

    // Check provider checkboxes
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('Anthropic')).toBeInTheDocument()
  })

  it('should display annual cost without AgentCostControl', () => {
    render(<CostCalculator />)

    // Check that the label exists
    expect(screen.getByText('Without AgentCostControl')).toBeInTheDocument()
    // Check that there's some dollar amount with /yr displayed
    const allCurrencyElements = screen.getAllByText(/\$[\d.]+K/)
    expect(allCurrencyElements.length).toBeGreaterThan(0)
  })

  it('should display savings amount', () => {
    render(<CostCalculator />)

    // Should show savings section
    expect(screen.getByText('Your Savings')).toBeInTheDocument()
    expect(screen.getByText(/reduction/)).toBeInTheDocument()
  })

  it('should update calculation when monthly spend changes', () => {
    render(<CostCalculator />)

    const slider = screen.getByRole('slider')
    fireEvent.change(slider, { target: { value: 10000 } })

    // $10K/month should update the display
    expect(screen.getByText('$10K')).toBeInTheDocument()
  })

  it('should update calculation when agent count changes', () => {
    render(<CostCalculator />)

    const agentInput = screen.getByRole('spinbutton')
    fireEvent.change(agentInput, { target: { value: 50 } })

    expect(agentInput).toHaveValue(50)

    // More agents should increase savings rate - look for percentage reduction text
    expect(screen.getByText(/% reduction/)).toBeInTheDocument()
  })

  it('should toggle provider selection', () => {
    render(<CostCalculator />)

    // OpenAI should be selected by default
    const openaiCheckbox = screen.getByRole('checkbox', { name: /openai/i })
    expect(openaiCheckbox).toBeChecked()

    // Click to deselect
    fireEvent.click(openaiCheckbox)
    expect(openaiCheckbox).not.toBeChecked()
  })

  it('should have CTA button linking to signup', () => {
    render(<CostCalculator />)

    const ctaButton = screen.getByRole('button', { name: /start saving today/i })
    expect(ctaButton).toBeInTheDocument()

    const link = ctaButton.closest('a')
    expect(link).toHaveAttribute('href', '/signup')
  })

  it('should display savings percentage', () => {
    render(<CostCalculator />)

    // Should show percentage reduction
    const percentageText = screen.getByText(/% reduction/)
    expect(percentageText).toBeInTheDocument()
  })

  it('should handle minimum spend value', () => {
    render(<CostCalculator />)

    const slider = screen.getByRole('slider')
    fireEvent.change(slider, { target: { value: 100 } })

    // $100/month should update the display - check for $100 text
    const elements = screen.getAllByText(/\$100/)
    expect(elements.length).toBeGreaterThan(0)
  })

  it('should handle maximum spend value', () => {
    render(<CostCalculator />)

    const slider = screen.getByRole('slider')
    fireEvent.change(slider, { target: { value: 100000 } })

    // $100K/month * 12 = $1.2M/year - check for $100K display
    expect(screen.getByText('$100K')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(<CostCalculator className="custom-class" />)

    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('should show all provider options', () => {
    render(<CostCalculator />)

    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('Anthropic')).toBeInTheDocument()
    expect(screen.getByText('Google AI')).toBeInTheDocument()
    expect(screen.getByText('Cohere')).toBeInTheDocument()
    expect(screen.getByText('Mistral')).toBeInTheDocument()
    expect(screen.getByText('Replicate')).toBeInTheDocument()
  })
})
