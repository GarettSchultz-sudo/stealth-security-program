# AgentCostControl - CHANGELOG

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-02-13

### Added
- Initial MVP release
- **Core Proxy Engine**
  - Anthropic Messages API compatible endpoint (`POST /v1/messages`)
  - OpenAI Chat Completions API compatible endpoint (`POST /v1/chat/completions`)
  - Streaming (SSE) support for both providers
  - Token counting with tiktoken
  - Cost calculation with comprehensive pricing data

- **Budget System**
  - Create, update, delete budgets
  - Per-user, per-agent, per-model scope
  - Daily, weekly, monthly periods
  - Warning and critical thresholds
  - Actions: alert, block, downgrade model

- **Smart Routing**
  - Rule-based model routing
  - Cost optimization rules
  - Savings estimation
  - Simulation endpoint

- **Analytics API**
  - Dashboard overview stats
  - Spend by model breakdown
  - Daily spend trend
  - Projected monthly spend

- **React Dashboard**
  - Responsive layout with sidebar navigation
  - Dashboard page with charts
  - Budget management
  - Integration guide

- **Infrastructure**
  - Docker Compose for local development
  - PostgreSQL database
  - Redis for caching
  - Production-ready Dockerfiles

### Technical Details
- Python 3.12+ with FastAPI
- SQLAlchemy 2.0 async ORM
- React 19 with TypeScript
- TailwindCSS v4
- Recharts for visualizations
