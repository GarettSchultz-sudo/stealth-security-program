# ClawShell

> The Protective Shell for Your AI Agents

**ClawShell** is an AI cost control and security platform built for the OpenClaw ecosystem. Track, budget, and optimize your AI agent spending while scanning for security vulnerabilities.

## Products

### 🐚 ClawShell (Cost Control)
- **Cost Tracking** - Real-time spend monitoring per user, agent, model
- **Budget Enforcement** - Block, alert, or auto-downgrade when limits hit
- **Smart Routing** - Route to cheaper models based on rules
- **Rate Limiting** - Per-key rate limits with sliding windows
- **Real-time Dashboard** - Live updates via Supabase Realtime

### 🛡️ ClawShell Scan (Security)
- **Trust Scoring** - 0-100 security scores for AI skills and agents
- **Vulnerability Detection** - Find secrets, injection risks, and misconfigurations
- **Continuous Monitoring** - Automated re-scanning of monitored skills
- **Compliance Reports** - SOC2, ISO27001, and custom frameworks

## Quick Start

1. Set up infrastructure (Vercel, Supabase, Upstash)
2. Copy `.env.example` to `.env.local` and fill in credentials
3. Run database migrations in Supabase SQL Editor
4. Deploy: `./scripts/deploy.sh`

## Usage with OpenClaw

```json
{
  "llm": {
    "provider": "anthropic",
    "baseUrl": "https://your-clawshell.vercel.app",
    "headers": {
      "x-clawshell-api-key": "cs_your_key_here"
    }
  }
}
```

## Brand

- **Product:** ClawShell (one word, capital C capital S)
- **Security sub-product:** ClawShell Scan
- **Package:** `clawshell`, `clawshell-scan`
- **Tagline:** "The protective shell for your Claw"

## License

MIT
