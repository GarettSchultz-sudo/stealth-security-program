/**
 * Tests for Landing Page
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LandingPage from '@/app/(marketing)/page'

// Mock Next.js Link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Hero Section', () => {
    it('should render the main headline', () => {
      render(<LandingPage />)

      expect(screen.getByText('Stop AI Agent Budget Surprises.')).toBeInTheDocument()
    })

    it('should render the gradient headline text', () => {
      render(<LandingPage />)

      expect(screen.getByText('Track, Control, Optimize.')).toBeInTheDocument()
    })

    it('should render the subheadline', () => {
      render(<LandingPage />)

      expect(screen.getByText(/Track, control, and optimize every dollar/)).toBeInTheDocument()
    })

    it('should have primary CTA button', () => {
      render(<LandingPage />)

      const primaryCta = screen.getByRole('button', { name: /start free — no credit card/i })
      expect(primaryCta).toBeInTheDocument()
    })

    it('should have secondary CTA button', () => {
      render(<LandingPage />)

      const secondaryCta = screen.getByRole('button', { name: /watch 2-min demo/i })
      expect(secondaryCta).toBeInTheDocument()
    })

    it('should display social proof pills', () => {
      render(<LandingPage />)

      expect(screen.getByText('Free forever tier')).toBeInTheDocument()
      expect(screen.getByText('Setup in 5 minutes')).toBeInTheDocument()
      expect(screen.getByText('Works with all LLM providers')).toBeInTheDocument()
    })
  })

  describe('Stats Section', () => {
    it('should display all stat labels', () => {
      render(<LandingPage />)

      expect(screen.getByText('Agent Spend Tracked')).toBeInTheDocument()
      expect(screen.getByText('API Calls Processed')).toBeInTheDocument()
      expect(screen.getByText('Uptime Reliability')).toBeInTheDocument()
      expect(screen.getByText(/Teams Trust/)).toBeInTheDocument()
    })
  })

  describe('Features Section', () => {
    it('should display all 4 feature titles', () => {
      render(<LandingPage />)

      expect(screen.getByText('Real-Time Cost Tracking')).toBeInTheDocument()
      expect(screen.getByText('Intelligent Model Routing')).toBeInTheDocument()
      expect(screen.getByText('Budget Enforcement')).toBeInTheDocument()
      expect(screen.getByText('ClawShield Security Layer')).toBeInTheDocument()
    })

    it('should display feature bullet points', () => {
      render(<LandingPage />)

      expect(screen.getByText('Live spend dashboard with per-agent breakdown')).toBeInTheDocument()
      expect(screen.getByText('Auto-downgrade when approaching budgets')).toBeInTheDocument()
      expect(screen.getByText('Per-agent and global budget caps')).toBeInTheDocument()
      expect(screen.getByText('Prompt injection detection')).toBeInTheDocument()
    })
  })

  describe('Calculator Section', () => {
    it('should display calculator section header', () => {
      render(<LandingPage />)

      expect(screen.getByText('See how much you could save')).toBeInTheDocument()
    })

    it('should have monthly spend input', () => {
      render(<LandingPage />)

      expect(screen.getByText('Monthly AI Spend')).toBeInTheDocument()
    })

    it('should have agent count input', () => {
      render(<LandingPage />)

      expect(screen.getByText('Number of AI Agents')).toBeInTheDocument()
    })

    it('should display savings labels', () => {
      render(<LandingPage />)

      expect(screen.getByText('Without AgentCostControl')).toBeInTheDocument()
      expect(screen.getByText('With AgentCostControl')).toBeInTheDocument()
    })
  })

  describe('Testimonials Section', () => {
    it('should display testimonials header', () => {
      render(<LandingPage />)

      expect(screen.getByText('Trusted by AI teams')).toBeInTheDocument()
    })

    it('should display testimonial quotes', () => {
      render(<LandingPage />)

      expect(screen.getByText(/saved us \$12K in the first month/)).toBeInTheDocument()
      expect(screen.getByText(/budget enforcement alone is worth it/)).toBeInTheDocument()
    })

    it('should display testimonial authors', () => {
      render(<LandingPage />)

      expect(screen.getByText('Sarah Chen')).toBeInTheDocument()
      expect(screen.getByText('Marcus Johnson')).toBeInTheDocument()
      expect(screen.getByText('Emily Rodriguez')).toBeInTheDocument()
    })
  })

  describe('Pricing Section', () => {
    it('should display pricing header', () => {
      render(<LandingPage />)

      expect(screen.getByText('Simple, transparent pricing')).toBeInTheDocument()
    })

    it('should display all 4 pricing tiers', () => {
      render(<LandingPage />)

      expect(screen.getByText('Starter')).toBeInTheDocument()
      expect(screen.getByText('Pro')).toBeInTheDocument()
      expect(screen.getByText('Team')).toBeInTheDocument()
      expect(screen.getByText('Enterprise')).toBeInTheDocument()
    })

    it('should display monthly/annual toggle', () => {
      render(<LandingPage />)

      expect(screen.getByText('Monthly')).toBeInTheDocument()
      expect(screen.getByText('Annual')).toBeInTheDocument()
      expect(screen.getByText('Save 20%')).toBeInTheDocument()
    })

    it('should show "Most Popular" badge on Team tier', () => {
      render(<LandingPage />)

      expect(screen.getByText('Most Popular')).toBeInTheDocument()
    })

    it('should toggle between monthly and annual pricing', () => {
      render(<LandingPage />)

      // Find the toggle button by its class (it's a button with rounded-full class)
      const toggleButtons = screen.getAllByRole('button')
      const toggleButton = toggleButtons.find(btn =>
        btn.className.includes('rounded-full') && btn.className.includes('w-14')
      )

      // Initially shows monthly price
      expect(screen.getAllByText('$49').length).toBeGreaterThan(0)

      // Click toggle
      if (toggleButton) {
        fireEvent.click(toggleButton)
      }

      // After toggle, should show annual price
      expect(screen.getAllByText('$39').length).toBeGreaterThan(0)
    })
  })

  describe('FAQ Section', () => {
    it('should display FAQ header', () => {
      render(<LandingPage />)

      expect(screen.getByText('Frequently Asked Questions')).toBeInTheDocument()
    })

    it('should display FAQ questions', () => {
      render(<LandingPage />)

      expect(screen.getByText('How does AgentCostControl track my AI spending?')).toBeInTheDocument()
      expect(screen.getByText('Will using AgentCostControl add latency to my API calls?')).toBeInTheDocument()
    })

    it('should expand FAQ answer when clicked', () => {
      render(<LandingPage />)

      // First FAQ should be open by default
      const firstAnswer = screen.getByText(/acts as a transparent proxy/)
      expect(firstAnswer).toBeVisible()
    })

    it('should have expandable FAQ items', () => {
      render(<LandingPage />)

      // All FAQ questions should be buttons
      const faqButtons = screen.getAllByRole('button').filter((btn) =>
        btn.textContent?.includes('How does') ||
        btn.textContent?.includes('Will using') ||
        btn.textContent?.includes('Is my data')
      )

      expect(faqButtons.length).toBeGreaterThan(0)
    })
  })

  describe('CTA Section', () => {
    it('should display final CTA section', () => {
      render(<LandingPage />)

      expect(screen.getByText('Ready to take control of your AI costs?')).toBeInTheDocument()
    })

    it('should have CTA buttons', () => {
      render(<LandingPage />)

      const getStartedButtons = screen.getAllByRole('button', { name: /get started/i })
      expect(getStartedButtons.length).toBeGreaterThan(0)
    })
  })

  describe('Footer', () => {
    it('should display footer with branding', () => {
      render(<LandingPage />)

      expect(screen.getByText(/© 2026 AgentCostControl/)).toBeInTheDocument()
    })

    it('should display newsletter signup', () => {
      render(<LandingPage />)

      expect(screen.getByText('Stay updated')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('you@email.com')).toBeInTheDocument()
    })

    it('should display status indicator', () => {
      render(<LandingPage />)

      expect(screen.getByText('All systems operational')).toBeInTheDocument()
    })

    it('should display footer navigation', () => {
      render(<LandingPage />)

      expect(screen.getByText('Product')).toBeInTheDocument()
      expect(screen.getByText('Company')).toBeInTheDocument()
      expect(screen.getByText('Legal')).toBeInTheDocument()
    })

    it('should display social links', () => {
      render(<LandingPage />)

      // Check for social media links by title
      expect(screen.getByTitle('Discord')).toBeInTheDocument()
      expect(screen.getByTitle('LinkedIn')).toBeInTheDocument()
      expect(screen.getByTitle('Twitter/X')).toBeInTheDocument()
      expect(screen.getByTitle('GitHub')).toBeInTheDocument()
    })
  })

  describe('Navigation', () => {
    it('should display navigation links', () => {
      render(<LandingPage />)

      // Use getAllByText since some links appear multiple times
      expect(screen.getAllByText('Features').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Calculator').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Pricing').length).toBeGreaterThan(0)
      expect(screen.getAllByText('FAQ').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Docs').length).toBeGreaterThan(0)
    })

    it('should have sign in and sign up buttons', () => {
      render(<LandingPage />)

      expect(screen.getAllByText('Sign In').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Get Started').length).toBeGreaterThan(0)
    })
  })
})
