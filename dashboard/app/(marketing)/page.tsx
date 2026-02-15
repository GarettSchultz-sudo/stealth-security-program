'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import {
  Shield,
  DollarSign,
  Zap,
  TrendingUp,
  CheckCircle,
  ArrowRight,
  Github,
  Mail,
  ShieldCheck,
  Target,
  BarChart3,
  AlertTriangle,
  Lock,
  Users,
  Clock,
  ChevronDown,
  Calculator,
  RefreshCw,
  Layers,
  Bot,
} from 'lucide-react'
import { Button } from '@/components/ui'

// Logo carousel data
const trustedLogos = [
  { name: 'OpenAI', opacity: 0.5 },
  { name: 'Anthropic', opacity: 0.5 },
  { name: 'Google AI', opacity: 0.5 },
  { name: 'Azure', opacity: 0.5 },
  { name: 'AWS', opacity: 0.5 },
  { name: 'Cohere', opacity: 0.5 },
  { name: 'Mistral', opacity: 0.5 },
  { name: 'Replicate', opacity: 0.5 },
]

// Updated stats with new values
const stats = [
  { value: '$2.3M+', label: 'Agent Spend Tracked' },
  { value: '50M+', label: 'API Calls Processed' },
  { value: '99.9%', label: 'Uptime Reliability' },
  { value: '500+', label: 'Teams Trust AgentCostControl' },
]

// 4 main features with alternating layout
const features = [
  {
    icon: DollarSign,
    title: 'Real-Time Cost Tracking',
    description: 'Monitor your AI spending across all providers with live updates. Know exactly where every dollar goes.',
    bullets: [
      'Live spend dashboard with per-agent breakdown',
      'Token-level cost attribution',
      'Multi-provider aggregation (OpenAI, Anthropic, Google, etc.)',
      'Historical trends and forecasting',
    ],
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-400/10',
  },
  {
    icon: RefreshCw,
    title: 'Intelligent Model Routing',
    description: 'Automatically switch between models based on cost, performance, and availability.',
    bullets: [
      'Auto-downgrade when approaching budgets',
      'Latency-aware routing for speed optimization',
      'Fallback chains for reliability',
      'Custom routing rules per agent',
    ],
    color: 'text-purple-400',
    bgColor: 'bg-purple-400/10',
  },
  {
    icon: Target,
    title: 'Budget Enforcement',
    description: 'Set hard and soft limits that prevent runaway AI costs before they happen.',
    bullets: [
      'Per-agent and global budget caps',
      'Graduated alerts at 50%, 75%, 90%',
      'Automatic request blocking at limits',
      'Rolling vs. fixed budget windows',
    ],
    color: 'text-teal-400',
    bgColor: 'bg-teal-400/10',
  },
  {
    icon: Shield,
    title: 'ClawShield Security Layer',
    description: 'Scan AI agents and skills for vulnerabilities before deployment.',
    bullets: [
      'Prompt injection detection',
      'Secrets and credential scanning',
      'Behavioral anomaly detection',
      'Compliance reporting (SOC2, HIPAA)',
    ],
    color: 'text-rose-400',
    bgColor: 'bg-rose-400/10',
  },
]

// 4-tier pricing
const pricingPlans = [
  {
    name: 'Starter',
    price: '$0',
    priceAnnual: '$0',
    period: 'forever',
    description: 'Perfect for trying out the platform',
    features: [
      '1,000 API calls/month',
      '1 budget',
      '7-day data retention',
      'Community support',
      'Basic analytics',
    ],
    cta: 'Start Free',
    ctaVariant: 'secondary' as const,
    popular: false,
  },
  {
    name: 'Pro',
    price: '$49',
    priceAnnual: '$39',
    period: '/month',
    description: 'For individual developers and small projects',
    features: [
      '50,000 API calls/month',
      'Unlimited budgets',
      '30-day data retention',
      'Email alerts',
      'Advanced analytics',
      'API access',
    ],
    cta: 'Start Pro Trial',
    ctaVariant: 'secondary' as const,
    popular: false,
  },
  {
    name: 'Team',
    price: '$199',
    priceAnnual: '$159',
    period: '/month',
    description: 'For teams building AI-powered products',
    features: [
      '500,000 API calls/month',
      'Team collaboration',
      '90-day data retention',
      'Slack + Discord alerts',
      'Priority support',
      'Custom routing rules',
      'SSO integration',
    ],
    cta: 'Start Team Trial',
    ctaVariant: 'primary' as const,
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    priceAnnual: 'Custom',
    period: '',
    description: 'For organizations with compliance needs',
    features: [
      'Unlimited API calls',
      'Dedicated support',
      'Custom retention',
      'SOC2 & HIPAA compliance',
      'On-premise option',
      'SLA guarantees',
      'Custom integrations',
    ],
    cta: 'Contact Sales',
    ctaVariant: 'secondary' as const,
    popular: false,
  },
]

// FAQ items
const faqs = [
  {
    question: 'How does AgentCostControl track my AI spending?',
    answer: 'AgentCostControl acts as a transparent proxy between your application and LLM providers. All API requests route through our system, where we log tokens, calculate costs using up-to-date pricing data, and attribute spend to specific agents or projects—all without adding latency.',
  },
  {
    question: 'Will using AgentCostControl add latency to my API calls?',
    answer: 'Our proxy adds less than 10ms of latency on average. We use edge computing and maintain direct peering relationships with major LLM providers. Most users report no noticeable difference in response times.',
  },
  {
    question: 'Is my data secure with AgentCostControl?',
    answer: 'Absolutely. We never store your prompt/response content—only metadata (tokens, model, timestamps). All data is encrypted in transit and at rest. We\'re SOC2 Type II certified and can sign BAAs for HIPAA compliance.',
  },
  {
    question: 'Which AI providers do you support?',
    answer: 'We support all major LLM providers: OpenAI (GPT-4, GPT-3.5), Anthropic (Claude), Google (Gemini), AWS Bedrock, Azure OpenAI, Cohere, Mistral AI, Replicate, and more. We also support custom endpoints.',
  },
  {
    question: 'What happens if I exceed my budget?',
    answer: 'You have full control. Configure soft alerts (email/Slack) at thresholds like 75% and 90%, or enable hard caps that block requests when limits are reached. You can also set up automatic model downgrades to stay within budget.',
  },
  {
    question: 'Can I cancel my subscription anytime?',
    answer: 'Yes, you can cancel anytime from your dashboard. Your access continues until the end of your billing period. We don\'t do long-term contracts or lock-ins.',
  },
  {
    question: 'Do you offer discounts for annual billing?',
    answer: 'Yes! Annual plans include a 20% discount compared to monthly billing. You can switch between monthly and annual at any time—prorated credits are applied automatically.',
  },
]

// Testimonials
const testimonials = [
  {
    quote: "AgentCostControl saved us $12K in the first month by catching a runaway agent loop we didn't know about.",
    author: "Sarah Chen",
    role: "CTO, AI Startup",
    avatar: "SC",
  },
  {
    quote: "The budget enforcement alone is worth it. No more surprise bills at the end of the month.",
    author: "Marcus Johnson",
    role: "Lead Engineer, FinTech",
    avatar: "MJ",
  },
  {
    quote: "ClawShield caught a prompt injection vulnerability in a third-party skill. That would have been a security incident.",
    author: "Emily Rodriguez",
    role: "VP Engineering, Enterprise",
    avatar: "ER",
  },
]

// FAQ Accordion Item component
function AccordionItem({ question, answer, isOpen, onClick }: {
  question: string
  answer: string
  isOpen: boolean
  onClick: () => void
}) {
  return (
    <div className="border border-slate-800 rounded-lg overflow-hidden">
      <button
        onClick={onClick}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-900/50 transition-colors"
      >
        <span className="font-medium text-white">{question}</span>
        <ChevronDown
          className={`text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          size={20}
        />
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${isOpen ? 'max-h-96' : 'max-h-0'}`}
      >
        <p className="p-4 pt-0 text-slate-400">{answer}</p>
      </div>
    </div>
  )
}

// Counter component for animated stats
function Counter({ value, suffix = '' }: { value: string; suffix?: string }) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const [hasAnimated, setHasAnimated] = useState(false)

  // Extract numeric value
  const numericValue = parseFloat(value.replace(/[^0-9.]/g, ''))
  const prefix = value.match(/^[^0-9]*/)?.[0] || ''
  const hasDecimal = value.includes('.')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated) {
          setHasAnimated(true)
          let start = 0
          const duration = 2000
          const increment = numericValue / (duration / 16)

          const timer = setInterval(() => {
            start += increment
            if (start >= numericValue) {
              setCount(numericValue)
              clearInterval(timer)
            } else {
              setCount(start)
            }
          }, 16)

          return () => clearInterval(timer)
        }
      },
      { threshold: 0.5 }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [numericValue, hasAnimated])

  return (
    <div ref={ref} className="text-3xl sm:text-4xl font-bold text-white font-mono">
      {prefix}{hasDecimal ? count.toFixed(1) : Math.floor(count).toLocaleString()}{suffix}
    </div>
  )
}

export default function LandingPage() {
  const [isAnnual, setIsAnnual] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg">
                <Shield className="text-white" size={20} />
              </div>
              <span className="text-lg font-bold text-white">
                Agent<span className="text-indigo-400">CostControl</span>
              </span>
            </Link>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors">Features</a>
              <a href="#calculator" className="text-sm text-slate-400 hover:text-white transition-colors">Calculator</a>
              <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</a>
              <a href="#faq" className="text-sm text-slate-400 hover:text-white transition-colors">FAQ</a>
              <a href="/docs" className="text-sm text-slate-400 hover:text-white transition-colors">Docs</a>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/login">
                <Button variant="ghost" size="sm">Sign In</Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="sm">Get Started</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 relative overflow-hidden">
        {/* Animated gradient orbs */}
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[100px] animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/20 rounded-full blur-[80px] animate-float-delayed" />
        <div className="absolute top-1/2 left-1/2 w-[300px] h-[300px] bg-teal-500/10 rounded-full blur-[60px] animate-float-slow" />

        <div className="max-w-7xl mx-auto text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-sm mb-6 animate-fade-in-up">
            <Zap size={14} />
            <span>Save up to 40% on AI costs with smart routing</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight animate-fade-in-up stagger-1">
            Stop AI Agent Budget Surprises.
            <br />
            <span className="bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Track, Control, Optimize.
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-8 animate-fade-in-up stagger-2">
            Track, control, and optimize every dollar your AI agents spend.
            Real-time cost visibility, budget enforcement, and security scanning—all in one platform.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 animate-fade-in-up stagger-3">
            <Link href="/signup">
              <Button
                variant="primary"
                size="lg"
                icon={ArrowRight}
                iconPosition="right"
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25"
              >
                Start Free — No Credit Card
              </Button>
            </Link>
            <Link href="/demo">
              <Button variant="secondary" size="lg">
                Watch 2-Min Demo
              </Button>
            </Link>
          </div>

          {/* Social Proof Pills */}
          <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-slate-500 mb-12 animate-fade-in-up stagger-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-400" />
              <span>Free forever tier</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-400" />
              <span>Setup in 5 minutes</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-400" />
              <span>Works with all LLM providers</span>
            </div>
          </div>

          {/* Logo Carousel */}
          <div className="relative overflow-hidden mb-12">
            <div className="absolute left-0 top-0 bottom-0 w-20 bg-gradient-to-r from-slate-950 to-transparent z-10" />
            <div className="absolute right-0 top-0 bottom-0 w-20 bg-gradient-to-l from-slate-950 to-transparent z-10" />
            <div className="animate-scroll flex gap-12 items-center">
              {[...trustedLogos, ...trustedLogos].map((logo, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-slate-500 whitespace-nowrap"
                  style={{ opacity: logo.opacity }}
                >
                  <div className="w-6 h-6 bg-slate-700 rounded" />
                  <span className="text-sm font-medium">{logo.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dashboard Preview */}
          <div className="mt-8 relative animate-scale-in">
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent z-10 pointer-events-none" />
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-2 shadow-2xl shadow-indigo-500/10">
              <div className="rounded-lg bg-slate-950 border border-slate-800 overflow-hidden">
                <div className="h-8 bg-slate-900 border-b border-slate-800 flex items-center px-3 gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="ml-4 text-xs text-slate-500">AgentCostControl Dashboard</span>
                </div>
                <div className="aspect-video bg-gradient-to-br from-slate-900 to-slate-950 flex items-center justify-center animate-shimmer">
                  <div className="text-center">
                    <BarChart3 size={48} className="mx-auto text-slate-700 mb-4" />
                    <p className="text-slate-600">Interactive Dashboard Preview</p>
                    <Link href="/demo" className="text-indigo-400 text-sm hover:underline mt-2 inline-block">
                      View live demo →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 border-y border-slate-800/50 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center fade-in-section">
                <Counter value={stat.value} />
                <div className="text-sm text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section - Alternating Layout */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Everything you need to control AI costs
            </h2>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
              Four powerful pillars that protect your budget and optimize your AI spending.
            </p>
          </div>

          <div className="space-y-20">
            {features.map((feature, index) => (
              <div
                key={feature.title}
                className={`grid lg:grid-cols-2 gap-12 items-center ${
                  index % 2 === 1 ? 'lg:flex-row-reverse' : ''
                }`}
              >
                <div className={index % 2 === 1 ? 'lg:order-2' : ''}>
                  <div className={`inline-flex p-3 rounded-xl ${feature.bgColor} mb-4`}>
                    <feature.icon className={feature.color} size={24} />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-4">{feature.title}</h3>
                  <p className="text-lg text-slate-400 mb-6">{feature.description}</p>
                  <ul className="space-y-3">
                    {feature.bullets.map((bullet) => (
                      <li key={bullet} className="flex items-start gap-3">
                        <CheckCircle size={20} className="text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-slate-300">{bullet}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className={`relative ${index % 2 === 1 ? 'lg:order-1' : ''}`}>
                  <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 card-hover">
                    <div className="h-48 bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg flex items-center justify-center">
                      <feature.icon className={`${feature.color} opacity-30`} size={80} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Cost Calculator Section */}
      <section id="calculator" className="py-20 px-4 bg-slate-900/30">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-sm mb-6">
              <Calculator size={14} />
              <span>Savings Calculator</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              See how much you could save
            </h2>
            <p className="text-lg text-slate-400">
              Calculate your potential savings with AgentCostControl&apos;s smart routing and budget enforcement.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Monthly AI Spend
                  </label>
                  <div className="text-3xl font-bold text-white font-mono">$5,000</div>
                  <input
                    type="range"
                    min="100"
                    max="100000"
                    defaultValue="5000"
                    className="w-full mt-2"
                  />
                  <div className="flex justify-between text-xs text-slate-500 mt-1">
                    <span>$100</span>
                    <span>$100K+</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Number of AI Agents
                  </label>
                  <input
                    type="number"
                    defaultValue="10"
                    min="1"
                    max="1000"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">
                    Providers Used
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {['OpenAI', 'Anthropic', 'Google', 'Cohere'].map((provider) => (
                      <label key={provider} className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-sm text-slate-400">{provider}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 rounded-xl p-6">
                <h4 className="text-lg font-semibold text-white mb-4">Estimated Savings</h4>

                <div className="space-y-4">
                  <div className="flex justify-between items-center py-3 border-b border-slate-700">
                    <span className="text-slate-400">Without AgentCostControl</span>
                    <span className="text-xl font-bold text-white font-mono">$60,000/yr</span>
                  </div>

                  <div className="flex justify-between items-center py-3 border-b border-slate-700">
                    <span className="text-slate-400">With AgentCostControl</span>
                    <span className="text-xl font-bold text-emerald-400 font-mono">$48,000/yr</span>
                  </div>

                  <div className="flex justify-between items-center py-3">
                    <span className="text-slate-300 font-medium">Your Savings</span>
                    <span className="text-2xl font-bold text-emerald-400 font-mono">$12,000/yr</span>
                  </div>
                </div>

                <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                  <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <TrendingUp size={16} />
                    <span>20% average savings through smart routing</span>
                  </div>
                </div>

                <Link href="/signup" className="block mt-6">
                  <Button variant="primary" className="w-full bg-gradient-to-r from-indigo-600 to-purple-600">
                    Start Saving Today
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Trusted by AI teams</h2>
            <p className="text-slate-400">See what teams are saying about AgentCostControl</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial) => (
              <div
                key={testimonial.author}
                className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 card-hover"
              >
                <p className="text-slate-300 mb-6">&quot;{testimonial.quote}&quot;</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-medium">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-medium text-white">{testimonial.author}</div>
                    <div className="text-sm text-slate-500">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section - 4 Tiers */}
      <section id="pricing" className="py-20 px-4 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-slate-400">
              Start free, upgrade when you need more. No hidden fees.
            </p>
          </div>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4 mb-12">
            <span className={`text-sm ${!isAnnual ? 'text-white' : 'text-slate-500'}`}>Monthly</span>
            <button
              onClick={() => setIsAnnual(!isAnnual)}
              className={`relative w-14 h-7 rounded-full transition-colors ${
                isAnnual ? 'bg-indigo-600' : 'bg-slate-700'
              }`}
            >
              <div
                className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                  isAnnual ? 'translate-x-8' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`text-sm ${isAnnual ? 'text-white' : 'text-slate-500'}`}>
              Annual
              <span className="ml-2 text-emerald-400 text-xs">Save 20%</span>
            </span>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`relative p-6 rounded-2xl border ${
                  plan.popular
                    ? 'bg-slate-900 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                    : 'bg-slate-900/50 border-slate-800'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-xs font-medium text-white">
                    Most Popular
                  </div>
                )}
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold text-white mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold text-white font-mono">
                      {isAnnual ? plan.priceAnnual : plan.price}
                    </span>
                    <span className="text-slate-500">{plan.period}</span>
                  </div>
                  <p className="text-sm text-slate-400 mt-2">{plan.description}</p>
                </div>
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <CheckCircle size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                      <span className="text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/signup" className="block">
                  <Button
                    variant={plan.ctaVariant}
                    className={`w-full ${
                      plan.popular
                        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500'
                        : ''
                    }`}
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Frequently Asked Questions</h2>
            <p className="text-slate-400">Everything you need to know about AgentCostControl</p>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <AccordionItem
                key={index}
                question={faq.question}
                answer={faq.answer}
                isOpen={openFaq === index}
                onClick={() => setOpenFaq(openFaq === index ? null : index)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 bg-gradient-to-b from-slate-900/30 to-slate-950">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            Ready to take control of your AI costs?
          </h2>
          <p className="text-lg text-slate-400 mb-8">
            Join hundreds of teams who trust AgentCostControl to manage
            their AI spending and keep their agents secure.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <Button
                variant="primary"
                size="lg"
                icon={ArrowRight}
                iconPosition="right"
                className="bg-gradient-to-r from-indigo-600 to-purple-600"
              >
                Get Started Free
              </Button>
            </Link>
            <Link href="/demo">
              <Button variant="secondary" size="lg">
                Try Interactive Demo
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer with Newsletter */}
      <footer className="border-t border-slate-800 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            {/* Brand + Newsletter */}
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="text-indigo-400" size={20} />
                <span className="font-bold text-white">AgentCostControl</span>
              </div>
              <p className="text-sm text-slate-500 mb-4">
                Track, control, and optimize your AI spending.
              </p>

              {/* Status Badge */}
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs text-slate-500">All systems operational</span>
              </div>

              {/* Newsletter */}
              <div>
                <p className="text-sm font-medium text-white mb-2">Stay updated</p>
                <div className="flex gap-2">
                  <input
                    type="email"
                    placeholder="you@email.com"
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  <Button variant="primary" size="sm" className="bg-indigo-600 hover:bg-indigo-500">
                    <Mail size={16} />
                  </Button>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-white mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="text-slate-400 hover:text-white transition-colors">Features</a></li>
                <li><a href="#calculator" className="text-slate-400 hover:text-white transition-colors">Calculator</a></li>
                <li><a href="#pricing" className="text-slate-400 hover:text-white transition-colors">Pricing</a></li>
                <li><a href="/docs" className="text-slate-400 hover:text-white transition-colors">Documentation</a></li>
                <li><a href="/changelog" className="text-slate-400 hover:text-white transition-colors">Changelog</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-white mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/about" className="text-slate-400 hover:text-white transition-colors">About</a></li>
                <li><a href="/blog" className="text-slate-400 hover:text-white transition-colors">Blog</a></li>
                <li><a href="/careers" className="text-slate-400 hover:text-white transition-colors">Careers</a></li>
                <li><a href="/contact" className="text-slate-400 hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/privacy" className="text-slate-400 hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="/terms" className="text-slate-400 hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="/security" className="text-slate-400 hover:text-white transition-colors">Security</a></li>
                <li><a href="/status" className="text-slate-400 hover:text-white transition-colors">Status</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-500">
              © 2026 AgentCostControl. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <a href="https://discord.gg/agentcostcontrol" className="text-slate-400 hover:text-white transition-colors" title="Discord">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
                </svg>
              </a>
              <a href="https://linkedin.com/company/agentcostcontrol" className="text-slate-400 hover:text-white transition-colors" title="LinkedIn">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
              </a>
              <a href="https://twitter.com/agentcostctrl" className="text-slate-400 hover:text-white transition-colors" title="Twitter/X">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              <a href="https://github.com/agentcostcontrol" className="text-slate-400 hover:text-white transition-colors" title="GitHub">
                <Github size={20} />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
