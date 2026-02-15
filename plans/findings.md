# Findings: AgentCostControl Execution Guide

## Technology Decisions (from Interview)

| Field | Decision | Rationale | Status |
|-------|----------|-----------|--------|
| backend_framework | FastAPI (Python) | Existing codebase, async support | Concrete |
| frontend_framework | Next.js 15 + React 19 | Existing codebase, TypeScript | Concrete |
| database | Supabase (PostgreSQL) | Existing, with RLS | Concrete |
| cache | Upstash Redis | Existing, for routing rules | Concrete |
| deployment | Vercel + Railway/Fly.io | Documented in MEMORY.md | Concrete |
| client_type | Web only | Dashboard, no separate client | Concrete |

## Gap Analysis (Phase 1 Complete)

### Critical Gaps

| ID | Location | Issue | Phase | Priority | Status |
|----|----------|-------|-------|----------|--------|
| GAP-001 | proxy/app/api/v1/auth.py:188 | `user_id` hardcoded with TODO: Auth | Phase 2 | Critical | **FIXED** |
| GAP-002 | proxy/app/api/v1/analytics.py:49 | `user_id` hardcoded with TODO: Auth | Phase 2 | Critical | **FIXED** |
| GAP-003 | proxy/app/api/v1/proxy.py:194,275 | `cost_usd: 0.0` with TODO: Calculate | Phase 3 | High | **FIXED** |
| GAP-004 | proxy/app/core/proxy_handler.py | SecurityEngine NOT imported/integrated | Phase 6 | Critical | Open |
| GAP-005 | proxy/app/scanners/scanner.py:237 | NotImplementedError for ClawHub API | Phase 6 | Medium | Open |

### Proxy Service Gaps

```
proxy/app/
├── api/v1/
│   ├── auth.py:188         # TODO: Auth - hardcoded user_id
│   ├── analytics.py:49     # TODO: Auth - hardcoded user_id
│   └── proxy.py:194,275    # TODO: Calculate actual cost
├── core/
│   └── proxy_handler.py    # MISSING: SecurityEngine integration
├── security/
│   └── engine.py           # EXISTS but not wired to proxy
├── scanners/
│   └── scanner.py:237      # NotImplementedError: ClawHub API
├── threat_intel/
│   └── __init__.py:153,158 # Empty pass statements
└── security/
    └── async_framework.py:330  # Empty pass statement
```

### Dashboard Gaps

```
dashboard/app/
├── agents/page.tsx:40      # Placeholder URL check for Supabase
└── api/stripe/             # MISSING: Stripe integration
```

### Database Status

| Migration | File | Status |
|-----------|------|--------|
| 001_initial | 001_initial.sql | Verified |
| 002_pricing | 002_pricing.sql | Verified |
| 003_agent_tasks | 003_agent_tasks.sql | Verified |
| 003_clawshield | 003_clawshield.sql | Verified |
| 004_alerts | 004_alerts.sql | Created (Phase 2) |
| Run all | 000_run_all.sql | Master migration |

**Seed data:** 91 LLM models, 16 providers in `supabase/seed.sql`

**SQLAlchemy Models:**
| Model | File | Status |
|-------|------|--------|
| User, ApiKey | user.py | Complete |
| Agent, AgentTask, AgentHeartbeat, TaskEvent | agent.py | Complete |
| ApiLog | api_log.py | Complete |
| Budget | budget.py | Complete |
| Alert | alert.py | Complete |
| RoutingRule | routing_rule.py | Complete |
| Pricing | pricing.py | Created (Phase 2) |
| ClawHubSkill, SkillScan, SkillFinding, etc. | scan.py | Complete |

### Security Engine Status

**EXISTS:** `proxy/app/security/engine.py` - Complete SecurityEngine class
- Coordinates all 6+ detectors
- Applies policies and thresholds
- Takes actions (block, warn, alert)
- Logs security events
- Manages quarantine

**MISSING:** Integration with proxy handler
- `proxy_handler.py` does NOT import SecurityEngine
- No security check before forwarding requests
- Detection results not logged

## File Ownership Matrix

### Wave 1 Teammates
| Teammate | Owns | Reads |
|----------|------|-------|
| database-dev | supabase/migrations/**, proxy/app/models/** | config files |
| proxy-dev | proxy/app/core/proxy_handler.py, stream*.py | models, config |
| budget-dev | budget_engine.py, api/v1/budgets.py | models, migrations |
| router-dev | smart_router.py, api/v1/routing.py | models, seed.sql |

### Wave 2 Teammates
| Teammate | Owns | Reads |
|----------|------|-------|
| security-dev | security/**, scanners/** | proxy_handler.py, scan.py |
| analytics-dev | analytics/**, api/v1/analytics.py | api_log.py, lib/** |
| payments-dev | api/stripe/**, webhooks/stripe/** | user.py, stripe.ts |
| microservices-dev | services/**, docker/** | proxy/**, dashboard/** |

## Critical Path Analysis

**Feature:** ClawShield Security Scanner

**Why Critical:**
1. SecurityEngine exists but NOT integrated (GAP-004)
2. Integration approach unclear (middleware vs wrapper vs sidecar)
3. Performance requirements strict (<10ms overhead)
4. Must be correct (security product)

**Approach:** Competing Hypotheses Pattern
1. Investigator A: Middleware-based integration
2. Investigator B: Wrapper-based integration
3. Investigator C: Sidecar service approach
4. Challenger: Devil's advocate selection

## Security Findings

### Existing Components (Ready)
- ✅ SecurityEngine class complete
- ✅ 6+ detector implementations
- ✅ Security config and models
- ✅ Rule engine for custom rules

### Missing Components (Need Work)
- ❌ SecurityEngine NOT imported in proxy_handler.py
- ❌ No security check before request forwarding
- ❌ Detection results not logged to database
- ❌ ClawHub API integration not implemented

### Recommendations
1. Wire SecurityEngine middleware in proxy_handler.py
2. Add security result logging to api_logs table
3. Implement blocking for HIGH/CRITICAL severity
4. Complete ClawHub API integration

## Performance Requirements

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Proxy overhead | <10ms | Response time delta |
| Budget check | <5ms | Internal timing |
| Router evaluation | <10ms | Rule processing time |
| ClawShield scan | <30s | Full skill scan |
| Concurrent requests | 100 | Load testing |

## Open Questions (None)

All technology decisions were concrete from the interview.

## Phase 1 Checkpoint

- [x] Gap analysis complete
- [x] Technology decisions documented
- [x] Critical path identified
- [x] File ownership matrix defined
- [x] Security findings documented

---

## Phase 4 Findings: Budget Engine

### Budget Engine Architecture

**Core Components:**
- `BudgetEngine` class - Main enforcement engine
- `BudgetDecision` dataclass - Result of budget checks
- `BudgetAlert` dataclass - Represents triggered alerts

**Alert Thresholds:**
- Standard thresholds: 50%, 75%, 90%, 100%
- Configurable warning threshold (default 80%)
- Configurable critical threshold (default 100%)

**Budget Actions:**
- `ALERT_ONLY` - Just send notification
- `BLOCK` - Block requests when exceeded
- `DOWNGRADE_MODEL` - Switch to cheaper model

**Budget Scopes:**
- `GLOBAL` - Applies to all usage
- `PER_AGENT` - Specific to one agent
- `PER_MODEL` - Specific to a model prefix
- `PER_WORKFLOW` - Specific to a workflow

**Reset Periods:**
- `DAILY` - Resets at midnight
- `WEEKLY` - Resets on Monday
- `MONTHLY` - Resets on 1st of month

### Budget API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /budgets | Create new budget |
| GET | /budgets | List all budgets |
| GET | /budgets/{id} | Get single budget |
| PUT | /budgets/{id} | Update budget |
| DELETE | /budgets/{id} | Soft delete budget |
| POST | /budgets/{id}/reset | Manually reset spend |
| GET | /budgets/status/summary | Comprehensive summary with alerts |
| GET | /budgets/{id}/status | Single budget status with thresholds |
| GET | /budgets/{id}/history | Daily usage history (1-365 days) |

### Integration Points

**Already Integrated:**
- `proxy_handler.py` creates `BudgetEngine` instance
- Budget checks called before each request
- Spend updates called after each request completes
- Streaming and standard requests both handled

**Callback Mechanism:**
- `BudgetEngine.__init__` accepts `alert_callback` parameter
- Callback receives `BudgetAlert` objects
- Can be wired to external notification systems (email, Slack, etc.)

### Key Findings

1. **Budget model already has all required fields:**
   - `limit_usd`, `current_spend_usd`, `reset_at`
   - `warning_threshold_percent`, `critical_threshold_percent`
   - `action_on_breach`, `downgrade_model`

2. **ApiLog model provides usage history data:**
   - `cost_usd`, `timestamp`, `total_tokens`
   - Indexed by `user_id`, `timestamp`

3. **Alert model exists but not wired to budget alerts:**
   - `AlertType.BUDGET_WARNING`, `AlertType.BUDGET_BREACH` defined
   - Delivery methods: email, Slack, Discord, generic webhook
   - Cooldown mechanism to prevent spam

---

## Phase 2 Findings: Database & Migrations

### Migration Structure

**All migrations verified and complete:**
- 001_initial.sql: Core tables (users, api_keys, api_logs, budgets, routing_rules)
- 002_pricing.sql: Pricing table for LLM cost lookup
- 003_agent_tasks.sql: Agent tracking (agents, agent_tasks, agent_heartbeats, task_events)
- 003_clawshield.sql: Security scanning tables
- 004_alerts.sql: Alert configuration (created in Phase 2)

### SQLAlchemy Model Coverage

**Models added in Phase 2:**
| Model | Description | Key Features |
|-------|-------------|--------------|
| Pricing | LLM pricing data | calculate_cost(), find_pricing() methods |
| AgentTask | Task tracking | Status, metrics, hierarchy support |
| AgentHeartbeat | Health monitoring | CPU, memory, queue tracking |
| TaskEvent | Audit trail | Event type, data, timestamps |

### Auth Implementation

**JWT-based authentication implemented:**
- `HTTPBearer` security scheme for token validation
- `get_current_user_id()` - Extracts user ID from JWT
- `get_current_user()` - Fetches full user model
- `CurrentUserId` and `CurrentUser` type aliases for dependency injection

**Endpoints secured:**
- All /api/v1/auth/* endpoints (except register/login)
- All /api/v1/analytics/* endpoints

### Seed Data Analysis

**91 LLM models across 16 providers:**
| Provider | Models | Price Range (input/1M) |
|----------|--------|------------------------|
| Anthropic | 10 | $0.25 - $15.00 |
| OpenAI | 11 | $0.15 - $50.00 |
| Google | 6 | $0.075 - $7.00 |
| DeepSeek | 7 | $0.14 - $0.55 |
| xAI | 7 | $0.30 - $12.00 |
| Mistral | 8 | $0.025 - $6.00 |
| Others | 42 | Various |

**Cache pricing available for:**
- Anthropic Claude models (cache_creation, cache_read)
- Google Gemini models

### Key Findings

1. **Database schema is complete and well-designed:**
   - RLS policies on all user-scoped tables
   - Proper foreign key constraints
   - Partitioning for api_logs (by month)

2. **Pricing model enables accurate cost tracking:**
   - Supports versioned pricing (effective_from/to)
   - Handles cache tokens for Anthropic
   - calculate_cost() handles all token types

3. **Auth gaps (GAP-001, GAP-002) resolved:**
   - JWT-based authentication with proper token validation
   - Dependency injection pattern for clean code
   - Type aliases for easy reuse across endpoints
