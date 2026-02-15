'use client'

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
} from 'lucide-react'
import { Button } from '@/components/ui'

const features = [
  {
    icon: DollarSign,
    title: 'Real-Time Cost Tracking',
    description: 'Monitor your AI spending across OpenAI, Anthropic, Google, and more in real-time.',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-400/10',
  },
  {
    icon: ShieldCheck,
    title: 'Security Scanning',
    description: 'Scan AI skills and agents for prompt injection, data leaks, and vulnerabilities.',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-400/10',
  },
  {
    icon: Zap,
    title: 'Automatic Model Switching',
    description: 'Automatically downgrade to cheaper models when approaching budget limits.',
    color: 'text-amber-400',
    bgColor: 'bg-amber-400/10',
  },
  {
    icon: Target,
    title: 'Trust Scores',
    description: 'Get actionable trust scores for AI skills before deploying them.',
    color: 'text-purple-400',
    bgColor: 'bg-purple-400/10',
  },
  {
    icon: BarChart3,
    title: 'Analytics Dashboard',
    description: 'Beautiful dashboards with cost trends, model performance, and usage insights.',
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/10',
  },
  {
    icon: AlertTriangle,
    title: 'Instant Alerts',
    description: 'Get notified via email, Slack, or Discord when budgets hit critical thresholds.',
    color: 'text-rose-400',
    bgColor: 'bg-rose-400/10',
  },
]

const pricingPlans = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Perfect for trying out the platform',
    features: [
      '50 security scans/month',
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
    price: '$29',
    period: '/month',
    description: 'For teams building AI products',
    features: [
      '500 scans/month',
      'Unlimited budgets',
      '90-day data retention',
      'Email + Slack alerts',
      'Advanced analytics',
      'API access',
      'Priority support',
    ],
    cta: 'Start Pro Trial',
    ctaVariant: 'primary' as const,
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For organizations with compliance needs',
    features: [
      'Unlimited scans',
      'SSO/SAML integration',
      'Custom retention',
      'SOC2 & HIPAA compliance',
      'Dedicated support',
      'On-premise option',
      'SLA guarantees',
    ],
    cta: 'Contact Sales',
    ctaVariant: 'secondary' as const,
    popular: false,
  },
]

const stats = [
  { value: '10M+', label: 'API requests tracked' },
  { value: '50K+', label: 'Security scans run' },
  { value: '99.9%', label: 'Uptime SLA' },
  { value: '<50ms', label: 'Alert latency' },
]

const testimonials = [
  {
    quote: "ClawShell saved us 40% on our OpenAI bill in the first month. The automatic model switching is a game-changer.",
    author: "Sarah Chen",
    role: "CTO, AI Startup",
    avatar: "SC",
  },
  {
    quote: "Finally, a platform that combines cost management with security. ClawShell Scan caught a prompt injection vulnerability we missed.",
    author: "Marcus Johnson",
    role: "Lead Engineer, FinTech",
    avatar: "MJ",
  },
  {
    quote: "The trust scores for ClawHub skills give us confidence before deploying agents to production.",
    author: "Emily Rodriguez",
    role: "VP Engineering, Enterprise",
    avatar: "ER",
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg">
                <Shield className="text-white" size={20} />
              </div>
              <span className="text-lg font-bold text-white">
                Claw<span className="text-cyan-400">Shell</span>
              </span>
            </Link>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</a>
              <a href="#security" className="text-sm text-slate-400 hover:text-white transition-colors">Security</a>
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
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-purple-500/5" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />

        <div className="max-w-7xl mx-auto text-center relative">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm mb-6">
            <Zap size={14} />
            <span>Save up to 40% on AI costs</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
            Secure Your AI Agents.
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Control Your Costs.
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-8">
            The unified platform for AI cost management and security scanning.
            Track spending, enforce budgets, and scan for vulnerabilities—all in one place.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link href="/signup">
              <Button variant="primary" size="lg" icon={ArrowRight} iconPosition="right">
                Start Free — No Credit Card
              </Button>
            </Link>
            <Link href="/demo">
              <Button variant="secondary" size="lg">
                Watch 2-Min Demo
              </Button>
            </Link>
          </div>

          {/* Social Proof */}
          <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-slate-500">
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

          {/* Dashboard Preview */}
          <div className="mt-16 relative">
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent z-10 pointer-events-none" />
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-2 shadow-2xl shadow-cyan-500/10">
              <div className="rounded-lg bg-slate-950 border border-slate-800 overflow-hidden">
                <div className="h-8 bg-slate-900 border-b border-slate-800 flex items-center px-3 gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="ml-4 text-xs text-slate-500">ClawShell Dashboard</span>
                </div>
                <div className="aspect-video bg-gradient-to-br from-slate-900 to-slate-950 flex items-center justify-center">
                  <div className="text-center">
                    <BarChart3 size={48} className="mx-auto text-slate-700 mb-4" />
                    <p className="text-slate-600">Interactive Dashboard Preview</p>
                    <Link href="/demo" className="text-cyan-400 text-sm hover:underline mt-2 inline-block">
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
      <section className="py-12 border-y border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-white font-mono">{stat.value}</div>
                <div className="text-sm text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Everything you need to manage AI costs and security
            </h2>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
              One platform to track spending, enforce budgets, scan for vulnerabilities,
              and keep your AI agents secure.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-all group"
              >
                <div className={`p-3 rounded-xl ${feature.bgColor} w-fit mb-4`}>
                  <feature.icon className={feature.color} size={24} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-slate-400">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="py-20 px-4 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm mb-6">
                <Lock size={14} />
                <span>Enterprise-Grade Security</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
                Built for security-conscious teams
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                ClawShell Scan scans AI skills and agents for OWASP LLM Top 10 vulnerabilities,
                including prompt injection, data leakage, and malicious patterns.
              </p>
              <ul className="space-y-4">
                {[
                  'Prompt injection detection',
                  'Secrets and credential scanning',
                  'Data exfiltration prevention',
                  'Behavioral anomaly detection',
                  'Compliance reporting (SOC2, GDPR, HIPAA)',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3">
                    <CheckCircle size={20} className="text-emerald-400 shrink-0" />
                    <span className="text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative">
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <ShieldCheck className="text-cyan-400" size={24} />
                  <span className="text-lg font-semibold text-white">Trust Score: 95/100</span>
                </div>
                <div className="h-3 bg-slate-800 rounded-full overflow-hidden mb-6">
                  <div className="h-full w-[95%] bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full" />
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'No secrets detected', status: 'pass' },
                    { label: 'No prompt injection', status: 'pass' },
                    { label: 'No malicious patterns', status: 'pass' },
                    { label: 'Dependencies secure', status: 'pass' },
                  ].map((check) => (
                    <div key={check.label} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                      <span className="text-slate-400">{check.label}</span>
                      <CheckCircle size={16} className="text-emerald-400" />
                    </div>
                  ))}
                </div>
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
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial) => (
              <div
                key={testimonial.author}
                className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800"
              >
                <p className="text-slate-300 mb-6">"{testimonial.quote}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-medium">
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

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-slate-400">
              Start free, upgrade when you need more. No hidden fees.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`relative p-6 rounded-2xl border ${
                  plan.popular
                    ? 'bg-slate-900 border-cyan-500/50 shadow-lg shadow-cyan-500/10'
                    : 'bg-slate-900/50 border-slate-800'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-cyan-500 text-xs font-medium text-white">
                    Most Popular
                  </div>
                )}
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold text-white mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold text-white font-mono">{plan.price}</span>
                    <span className="text-slate-500">{plan.period}</span>
                  </div>
                  <p className="text-sm text-slate-400 mt-2">{plan.description}</p>
                </div>
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      <CheckCircle size={16} className="text-emerald-400 shrink-0" />
                      <span className="text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/signup" className="block">
                  <Button variant={plan.ctaVariant} className="w-full">
                    {plan.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            Ready to take control of your AI costs?
          </h2>
          <p className="text-lg text-slate-400 mb-8">
            Join thousands of developers who trust ClawShell to manage
            their AI spending and keep their agents secure.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <Button variant="primary" size="lg" icon={ArrowRight} iconPosition="right">
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

      {/* Footer */}
      <footer className="border-t border-slate-800 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="text-cyan-400" size={20} />
                <span className="font-bold text-white">ClawShell</span>
              </div>
              <p className="text-sm text-slate-500">
                Secure your AI agents. Control your costs.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-white mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="text-slate-400 hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="text-slate-400 hover:text-white transition-colors">Pricing</a></li>
                <li><a href="/demo" className="text-slate-400 hover:text-white transition-colors">Demo</a></li>
                <li><a href="/docs" className="text-slate-400 hover:text-white transition-colors">Documentation</a></li>
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
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-500">
              © 2026 ClawShell. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <a href="https://github.com" className="text-slate-400 hover:text-white transition-colors">
                <Github size={20} />
              </a>
              <a href="https://twitter.com" className="text-slate-400 hover:text-white transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
