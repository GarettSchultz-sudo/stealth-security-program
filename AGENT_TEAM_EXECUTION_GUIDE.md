# Agent Team Execution Guide for MVP_LAUNCH_CHECKLIST.md

**Purpose**: Full Production - Production-ready AI Cost Control Proxy with monitoring, scaling, and hardening for 100-1000 global users.

**Execution Order**: Step 0 -> Phase 1 -> Phase 2 -> Phase 3-6 (parallel) -> Phase 7-9 (parallel) -> Phase D -> Phase F

**State Continuity**: Each phase reads accumulated state from `task_plan.md`, `findings.md`, `progress.md`, and Memory MCP entities written by prior phases/teammates.

**Team Topology**: Swarm (4 waves: 0 lead-solo, 1 parallel, 2 parallel, 3 lead-solo)

**Control Flow**: Per-wave teams with full isolation. Teams created and destroyed per wave. Maximum parallelism.

**Open Research**: 0 fields require research resolution in Phase 1 before implementation can begin. All technology decisions are concrete.

---

## Input Criteria Summary

```yaml
project_name: "AgentCostControl"
project_slug: "agentcostcontrol"
prompt_file: "MVP_LAUNCH_CHECKLIST.md"
goal_summary: "Full Production - Production-ready AI Cost Control Proxy with monitoring, scaling, and hardening"

tech_stack:
  backend_framework:
    value: "FastAPI"
  backend_language:
    value: "Python"
  frontend_framework:
    value: "Next.js 15 + React 19 + TypeScript"
  database:
    value: "Supabase (PostgreSQL) with RLS"
  cache:
    value: "Upstash Redis"
  deployment:
    value: "Vercel (dashboard) + Railway/Fly.io (proxy)"
  client_type:
    value: "Web only"

services:
  value:
    - "dashboard"
    - "proxy"
    - "services/auth"
    - "services/budget"
    - "services/routing"
    - "services/analytics"
    - "services/payments"

service_base_path: "services"
service_entry_file: "main.py"

hosting:
  value: "Vercel + Railway/Fly.io"
target_users:
  value: "100-1000 users"
geo_distribution:
  value: "Global"

features:
  - name: "Database & Migrations"
    category: "data"
    critical_path: false
    approach:
      value: "Supabase migrations with RLS policies"
  - name: "LLM Proxy Handler"
    category: "proxy"
    critical_path: false
    approach:
      value: "FastAPI with streaming support for Anthropic and OpenAI"
  - name: "Budget Engine"
    category: "budget"
    critical_path: false
    approach:
      value: "Real-time budget tracking with enforcement middleware"
  - name: "Smart Router"
    category: "routing"
    critical_path: false
    approach:
      value: "Cost optimization with model fallback rules"
  - name: "Security Scanner (ClawShield)"
    category: "security"
    critical_path: true
    approach:
      research: "Compare middleware-based vs wrapper-based vs sidecar integration"
      constraints: ["Must scan before request forwards", "Must support async detection"]
  - name: "Analytics & Dashboards"
    category: "analytics"
    critical_path: false
    approach:
      value: "Real-time dashboard with cost visualizations"
  - name: "Payments & Billing"
    category: "payments"
    critical_path: false
    approach:
      value: "Stripe checkout with webhook handling"

team_topology: "swarm"

team_config:
  team_name: "agentcostcontrol-build"
  delegate_lead: true
  require_plan_approval: true
  default_teammate_model: "sonnet"
  waves:
    - wave: 0
      mode: "lead-solo"
      phases: ["step0", "phase1"]
    - wave: 1
      mode: "parallel"
      phases: ["phase2", "phase3", "phase4", "phase5"]
      teammates:
        - name: "database-dev"
          phase: "phase2"
          subagent_type: "general-purpose"
        - name: "proxy-dev"
          phase: "phase3"
          subagent_type: "general-purpose"
        - name: "budget-dev"
          phase: "phase4"
          subagent_type: "general-purpose"
        - name: "router-dev"
          phase: "phase5"
          subagent_type: "general-purpose"
    - wave: 2
      mode: "parallel"
      phases: ["phase6", "phase7", "phase8", "phase9"]
      teammates:
        - name: "security-dev"
          phase: "phase6"
          subagent_type: "general-purpose"
        - name: "analytics-dev"
          phase: "phase7"
          subagent_type: "general-purpose"
        - name: "payments-dev"
          phase: "phase8"
          subagent_type: "general-purpose"
        - name: "microservices-dev"
          phase: "phase9"
          subagent_type: "general-purpose"
    - wave: 3
      mode: "lead-solo"
      phases: ["phaseD", "phaseF"]
  quality_gates:
    require_tests_pass: true
    require_code_review: true
    require_memory_checkpoint: true

success_criteria:
  functional:
    - value: "Proxy intercepts Anthropic /v1/messages and OpenAI /v1/chat/completions"
    - value: "Budget enforcement blocks requests when limit exceeded"
    - value: "Smart router applies cost optimization rules"
    - value: "ClawShield scans for prompt injection, secrets, and malware patterns"
    - value: "Analytics dashboard shows spend by model, provider, and agent"
    - value: "Payment integration creates Stripe checkout sessions"
  infrastructure:
    - value: "SSL/TLS on all services"
    - value: "Automated database backups"
    - value: "Sentry monitoring configured"
    - value: "Health monitoring active"
  deployment:
    - value: "Single command deploy"
    - value: "Environment docs in .env.example"
    - value: "Setup documentation complete"
  performance:
    - value: "Proxy latency < 10ms overhead"
    - value: "100 concurrent requests supported"
    - value: "High availability (99.9% target)"
```

---

## Core Concept: Teams as the Execution Primitive

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENTCOSTCONTROL EXECUTION MODEL                 │
├──────────────────────────────────┬──────────────────────────────────────┤
│  Wave 0 (Lead-Solo)              │  Bootstrap + Assessment              │
│  ├── Step 0: Bootstrap           │  Planning files, Memory, Serena      │
│  └── Phase 1: Assessment         │  Gap analysis (no research needed)   │
├──────────────────────────────────┼──────────────────────────────────────┤
│  Wave 1 (Parallel - 4 teammates) │  Foundation Features                 │
│  ├── Phase 2: Database           │  supabase/migrations/**              │
│  ├── Phase 3: LLM Proxy          │  proxy/app/core/proxy_handler.py     │
│  ├── Phase 4: Budget Engine      │  proxy/app/core/budget_engine.py     │
│  └── Phase 5: Smart Router       │  proxy/app/core/smart_router.py      │
├──────────────────────────────────┼──────────────────────────────────────┤
│  Wave 2 (Parallel - 4 teammates) │  Advanced Features                   │
│  ├── Phase 6: ClawShield         │  proxy/app/security/** (CRITICAL)    │
│  ├── Phase 7: Analytics          │  dashboard/app/analytics/**          │
│  ├── Phase 8: Payments           │  dashboard/app/api/stripe/**         │
│  └── Phase 9: Microservices      │  services/**, docker/**              │
├──────────────────────────────────┼──────────────────────────────────────┤
│  Wave 3 (Lead-Solo)              │  Final Validation                    │
│  ├── Phase D: Deployment         │  Vercel + Railway/Fly.io             │
│  └── Phase F: Testing            │  Unit, Integration, Security, Load   │
└──────────────────────────────────┴──────────────────────────────────────┘
```

---

## Step 0: Bootstrap

**Purpose**: Initialize all tools, register project, load prior context, set up planning files.
**Depends on**: Nothing (this is first)
**Produces**: Serena onboarded, Memory initialized, planning files created, team config stored
**Assigned to**: Lead (always)

### Swarm Topology Execution

```
# 1. Lead runs bootstrap tasks directly
1. mcp__serena__check_onboarding_performed() - check if project is registered
2. mcp__serena__onboarding() - register project if not already done
3. mcp__serena__initial_instructions() - read Serena operating manual
4. mcp__memory__read_graph() - check for any prior context from previous sessions
5. mcp__memory__search_nodes('agentcostcontrol') - find related prior work
6. /planning-with-files:plan 'AgentCostControl - Full Production'
7. Verify task_plan.md, findings.md, progress.md are created
8. mcp__memory__create_entities([{
     name: 'Project_agentcostcontrol_Start',
     entityType: 'milestone',
     observations: [
       'Full Production - Production-ready AI Cost Control Proxy',
       'Target: Vercel + Railway/Fly.io, 100-1000 users, Global',
       'Open research questions: 0 (all tech decisions concrete)',
       'Team topology: swarm'
     ]
   }])
9. /checkpoint:create 'pre-assessment-bootstrap'

DONE WHEN: Serena onboarded, Memory initialized, planning files exist, checkpoint saved.
```

---

## Phase 1: Assessment + Technology Selection

**Purpose**: Full gap analysis of the codebase. All technology decisions are already concrete.
**Depends on**: Step 0 (Serena onboarded, planning files exist)
**Produces**: Populated `findings.md`, detailed `task_plan.md`, Memory entities with assessment results
**Assigned to**: Lead (solo - no research needed since all tech is concrete)

### Lead Runs Directly

```
Execute MVP_LAUNCH_CHECKLIST.md Phase 1: Assessment + Technology Selection.

Read task_plan.md and progress.md for current state.

PART A: TECHNOLOGY DECISIONS (ALL CONCRETE - NO RESEARCH)
=========================================================
All technology decisions are already resolved:

| Field | Decision | Status |
|-------|----------|--------|
| backend_framework | FastAPI | Concrete |
| backend_language | Python | Concrete |
| frontend_framework | Next.js 15 + React 19 | Concrete |
| database | Supabase (PostgreSQL) | Concrete |
| cache | Upstash Redis | Concrete |
| deployment | Vercel + Railway/Fly.io | Concrete |
| client_type | Web only | Concrete |

Store as Memory entities:
- mcp__memory__create_entities([{name: 'Decision_backend_framework', ...}])
- mcp__memory__create_entities([{name: 'Decision_database', ...}])
- (etc. for all fields)

PART B: CODEBASE GAP ANALYSIS
==============================
1. GAP ANALYSIS:
   - Search for: TODO|FIXME|mock|stub|placeholder|NotImplemented
   - Locations: proxy/, dashboard/, supabase/migrations/
   - Document every gap found in findings.md

2. MIGRATION STATUS:
   - Verify all 4 migrations are applied
   - Check seed.sql has 91 model pricing data

3. SECURITY AUDIT:
   - Review proxy/app/security/ completeness
   - Check for hardcoded user_id placeholders
   - Verify security engine is wired to proxy handler

4. ARCHITECTURE EVALUATION:
   - Evaluate microservices readiness
   - Check current service boundaries
   - Document inter-service communication gaps

PART C: SYNTHESIZE
===================
- Compile gap analysis into findings.md
- Create task_plan.md with per-phase breakdown
- Update progress.md with Phase 1 completion
- /checkpoint:create 'phase1-assessment-complete'

DONE WHEN:
  1. findings.md has comprehensive gap analysis
  2. task_plan.md has detailed phase breakdown
  3. All technology decisions stored in Memory
```

---

## Wave 1: Foundation Features (4 Parallel Teammates)

### Phase 2: Database & Migrations

**Purpose**: Apply Supabase migrations, complete models, seed pricing data.
**Depends on**: Phase 1
**Produces**: All tables created, RLS policies active, 91 model pricing seeded
**Task ID**: `phase2`

```
You are database-dev on team agentcostcontrol-wave-1.

Execute MVP_LAUNCH_CHECKLIST.md Phase 2: Database & Migrations.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase2', owner='database-dev', status='in_progress')

IMPLEMENTATION:
1. MIGRATIONS (supabase/migrations/):
   - Review all 4 migration files
   - Apply pending migrations
   - Verify RLS policies are active

2. MODELS (proxy/app/models/):
   - Complete any incomplete model definitions
   - Add missing relationships
   - Verify SQLAlchemy async patterns

3. SEED DATA (supabase/seed.sql):
   - Verify 91 model pricing entries
   - Check 16 provider coverage
   - Add any missing model entries

4. TESTING:
   - Verify all tables exist
   - Test RLS policies
   - Validate seed data integrity

FILE OWNERSHIP (parallel safety):
- You OWN: supabase/migrations/**, proxy/app/models/**
- You READ: proxy/app/config.py, dashboard/lib/supabase.ts (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase2 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase2', status='completed')
- mcp__memory__create_entities for database decisions
- /checkpoint:create 'phase2-database-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 2 complete. All migrations applied, 91 models seeded.', summary='Phase 2 done')
```

### Phase 3: LLM Proxy Handler

**Purpose**: Complete streaming proxy for Anthropic and OpenAI endpoints.
**Depends on**: Phase 1
**Produces**: Working proxy with streaming, error handling, token counting
**Task ID**: `phase3`

```
You are proxy-dev on team agentcostcontrol-wave-1.

Execute MVP_LAUNCH_CHECKLIST.md Phase 3: LLM Proxy Handler.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase3', owner='proxy-dev', status='in_progress')

IMPLEMENTATION:
1. PROXY HANDLER (proxy/app/core/proxy_handler.py):
   - Complete Anthropic /v1/messages endpoint
   - Complete OpenAI /v1/chat/completions endpoint
   - Implement streaming support
   - Add error handling and retries

2. STREAMING (proxy/app/core/stream_handler.py):
   - Implement SSE streaming
   - Handle chunk parsing
   - Add timeout handling

3. TOKEN COUNTING (proxy/app/core/token_counter.py):
   - Implement token estimation
   - Add token logging to api_logs table

4. TESTING:
   - Test Anthropic streaming
   - Test OpenAI streaming
   - Test error scenarios

FILE OWNERSHIP (parallel safety):
- You OWN: proxy/app/core/proxy_handler.py, proxy/app/core/stream*.py, proxy/app/core/token_counter.py
- You READ: proxy/app/models/**, proxy/app/config.py (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase3 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase3', status='completed')
- mcp__memory__create_entities for proxy decisions
- /checkpoint:create 'phase3-proxy-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 3 complete. LLM proxy with streaming operational.', summary='Phase 3 done')
```

### Phase 4: Budget Engine

**Purpose**: Implement budget tracking and enforcement.
**Depends on**: Phase 1, Phase 2 (for database)
**Produces**: Budget enforcement middleware, real-time tracking, alerts
**Task ID**: `phase4`

```
You are budget-dev on team agentcostcontrol-wave-1.

Execute MVP_LAUNCH_CHECKLIST.md Phase 4: Budget Engine.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase4', owner='budget-dev', status='in_progress')

IMPLEMENTATION:
1. BUDGET ENGINE (proxy/app/core/budget_engine.py):
   - Implement budget check logic
   - Add real-time spend tracking
   - Create budget enforcement middleware
   - Implement budget reset logic

2. API ROUTES (proxy/app/api/v1/budgets.py):
   - Complete budget CRUD operations
   - Add budget status endpoint
   - Implement budget alert configuration

3. TESTING:
   - Test budget enforcement blocks requests
   - Test budget tracking accuracy
   - Test alert triggers

FILE OWNERSHIP (parallel safety):
- You OWN: proxy/app/core/budget_engine.py, proxy/app/api/v1/budgets.py
- You READ: proxy/app/models/budget.py, supabase/migrations/** (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase4 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase4', status='completed')
- mcp__memory__create_entities for budget decisions
- /checkpoint:create 'phase4-budget-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 4 complete. Budget enforcement active.', summary='Phase 4 done')
```

### Phase 5: Smart Router

**Purpose**: Implement cost optimization with intelligent model routing.
**Depends on**: Phase 1, Phase 2 (for database)
**Produces**: Routing rules engine, model fallback, cost optimization
**Task ID**: `phase5`

```
You are router-dev on team agentcostcontrol-wave-1.

Execute MVP_LAUNCH_CHECKLIST.md Phase 5: Smart Router.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase5', owner='router-dev', status='in_progress')

IMPLEMENTATION:
1. SMART ROUTER (proxy/app/core/smart_router.py):
   - Implement routing rule evaluation
   - Add cost optimization logic
   - Create model fallback chains
   - Implement load balancing

2. API ROUTES (proxy/app/api/v1/routing.py):
   - Complete routing rule CRUD
   - Add routing test endpoint
   - Implement rule priority

3. PRICING DATA (proxy/app/core/pricing_data.py):
   - Wire to seed data
   - Add real-time pricing updates

4. TESTING:
   - Test routing rule evaluation
   - Test model fallback
   - Test cost optimization

FILE OWNERSHIP (parallel safety):
- You OWN: proxy/app/core/smart_router.py, proxy/app/api/v1/routing.py, proxy/app/core/pricing_data.py
- You READ: proxy/app/models/routing_rule.py, supabase/seed.sql (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase5 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase5', status='completed')
- mcp__memory__create_entities for routing decisions
- /checkpoint:create 'phase5-router-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 5 complete. Smart routing operational.', summary='Phase 5 done')
```

---

## Wave 2: Advanced Features (4 Parallel Teammates)

### Phase 6: ClawShield Security (CRITICAL PATH - Competing Hypotheses)

**Purpose**: Complete security scanner with all detection patterns.
**Depends on**: Phase 1, Phase 3 (for proxy integration)
**Produces**: Working security engine with 6+ detectors, wired to proxy
**Task ID**: `phase6`
**Critical Path**: YES - Use competing hypotheses pattern

```
You are security-dev on team agentcostcontrol-wave-2.

Execute MVP_LAUNCH_CHECKLIST.md Phase 6: ClawShield Security. THIS IS THE CRITICAL PATH.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase6', owner='security-dev', status='in_progress')

COMPETING HYPOTHESES (run before implementation):
=================================================
Research integration approaches:
1. Middleware-based: Security check before proxy forwards
2. Wrapper-based: Wrap each provider client
3. Sidecar service: Separate scanning service

Pick approach based on:
- Latency impact (<10ms requirement)
- Accuracy of detection
- Maintainability

IMPLEMENTATION:
1. SECURITY ENGINE (proxy/app/security/engine.py):
   - Complete security orchestrator
   - Implement async detection pipeline
   - Add result aggregation

2. DETECTORS (proxy/app/security/detectors/):
   - prompt_injection.py - Prompt injection detection
   - credential.py - Secret/credential detection
   - data_exfil.py - Data exfiltration detection
   - runaway.py - Runaway agent detection
   - anomaly.py - Anomaly detection
   - semantic.py - Semantic analysis
   - tool_abuse.py - Tool abuse detection

3. MIDDLEWARE (proxy/app/security/middleware.py):
   - Wire security check to proxy handler
   - Implement request/response scanning
   - Add blocking for high-severity findings

4. SCANNERS (proxy/app/scanners/):
   - Complete scanner.py
   - Implement trust_scorer.py
   - Add patterns.py

5. TESTING:
   - Test all 6+ detector types
   - Test blocking behavior
   - Test performance (<30s for typical skill)

FILE OWNERSHIP (parallel safety):
- You OWN: proxy/app/security/**, proxy/app/scanners/**
- You READ: proxy/app/core/proxy_handler.py, proxy/app/models/scan.py (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase6 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase6', status='completed')
- mcp__memory__create_entities for security decisions
- /checkpoint:create 'phase6-security-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 6 complete. ClawShield security operational with all detectors.', summary='Phase 6 done')
```

### Phase 7: Analytics & Dashboards

**Purpose**: Complete analytics API and dashboard visualizations.
**Depends on**: Phase 1, Phase 2 (for database)
**Produces**: Working analytics API, dashboard with charts
**Task ID**: `phase7`

```
You are analytics-dev on team agentcostcontrol-wave-2.

Execute MVP_LAUNCH_CHECKLIST.md Phase 7: Analytics & Dashboards.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase7', owner='analytics-dev', status='in_progress')

IMPLEMENTATION:
1. ANALYTICS API (proxy/app/api/v1/analytics.py):
   - Complete spend aggregation endpoints
   - Add model usage breakdown
   - Implement provider comparison
   - Add time-series data

2. DASHBOARD (dashboard/app/analytics/):
   - Complete cost visualizations
   - Add model usage charts
   - Implement provider breakdown
   - Add real-time updates

3. TESTING:
   - Test aggregation accuracy
   - Test chart rendering
   - Test real-time updates

FILE OWNERSHIP (parallel safety):
- You OWN: dashboard/app/analytics/**, proxy/app/api/v1/analytics.py
- You READ: proxy/app/models/api_log.py, dashboard/lib/** (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase7 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase7', status='completed')
- mcp__memory__create_entities for analytics decisions
- /checkpoint:create 'phase7-analytics-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 7 complete. Analytics dashboard operational.', summary='Phase 7 done')
```

### Phase 8: Payments & Billing

**Purpose**: Complete Stripe integration for subscriptions.
**Depends on**: Phase 1, Phase 2 (for database)
**Produces**: Working checkout, webhooks, subscription management
**Task ID**: `phase8`

```
You are payments-dev on team agentcostcontrol-wave-2.

Execute MVP_LAUNCH_CHECKLIST.md Phase 8: Payments & Billing.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase8', owner='payments-dev', status='in_progress')

IMPLEMENTATION:
1. STRIPE INTEGRATION (dashboard/app/api/stripe/):
   - Create checkout session endpoint
   - Implement customer portal
   - Add subscription management

2. WEBHOOKS (dashboard/app/api/webhooks/stripe/):
   - Handle checkout.session.completed
   - Handle invoice.paid
   - Handle subscription updates

3. USER MODEL UPDATES:
   - Add Stripe customer ID field
   - Add subscription status tracking

4. TESTING:
   - Test checkout flow
   - Test webhook handling
   - Test subscription status updates

FILE OWNERSHIP (parallel safety):
- You OWN: dashboard/app/api/stripe/**, dashboard/app/api/webhooks/stripe/**
- You READ: proxy/app/models/user.py, dashboard/lib/stripe.ts (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase8 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase8', status='completed')
- mcp__memory__create_entities for payments decisions
- /checkpoint:create 'phase8-payments-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 8 complete. Stripe payments operational.', summary='Phase 8 done')
```

### Phase 9: Microservices Architecture

**Purpose**: Extract services for independent deployment.
**Depends on**: Phase 1, Phases 2-8 (service implementations)
**Produces**: Separate deployable services, Docker configs
**Task ID**: `phase9`

```
You are microservices-dev on team agentcostcontrol-wave-2.

Execute MVP_LAUNCH_CHECKLIST.md Phase 9: Microservices Architecture.

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for technology decisions
3. TaskList() → claim your task: TaskUpdate(taskId='phase9', owner='microservices-dev', status='in_progress')

IMPLEMENTATION:
1. SERVICE EXTRACTION (services/):
   - Extract auth service: services/auth/
   - Extract budget service: services/budget/
   - Extract routing service: services/routing/
   - Each service gets: main.py, routes/, models/

2. DOCKER CONFIGURATION (docker/):
   - Create Dockerfile per service
   - Create docker-compose.yml
   - Add health checks

3. INTER-SERVICE COMMUNICATION:
   - Configure REST API calls
   - Set up shared database access
   - Add service discovery

4. TESTING:
   - Test service isolation
   - Test inter-service communication
   - Test docker-compose deployment

FILE OWNERSHIP (parallel safety):
- You OWN: services/**, docker/**, docker-compose.yml
- You READ: proxy/**, dashboard/** (do not edit)

WHEN DONE:
- Update task_plan.md: mark phase9 as complete
- Update progress.md: final summary
- TaskUpdate(taskId='phase9', status='completed')
- mcp__memory__create_entities for microservices decisions
- /checkpoint:create 'phase9-microservices-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase 9 complete. Microservices architecture ready.', summary='Phase 9 done')
```

---

## Phase D: Deployment & Hardening

**Purpose**: Production-grade deployment with SSL, secrets, monitoring, backup.
**Depends on**: All feature phases (2-9)
**Produces**: Production deployment, monitoring, backups
**Task ID**: `phaseD`
**Assigned to**: Lead (solo)

### Lead Runs Directly

```
Execute MVP_LAUNCH_CHECKLIST.md Phase D: Deployment & Hardening.

Read task_plan.md, findings.md, progress.md for context.
Read Memory: mcp__memory__search_nodes('Decision_') for resolved decisions.

IMPLEMENTATION:

1. VERCEL DEPLOYMENT (dashboard):
   - Configure Vercel project
   - Set environment variables
   - Deploy dashboard
   - Configure custom domain (if applicable)

2. RAILWAY/FLY.IO DEPLOYMENT (proxy + services):
   - Configure Railway/Fly.io project
   - Set environment variables
   - Deploy proxy service
   - Deploy microservices

3. SSL/TLS:
   - Verify HTTPS on all endpoints
   - Configure SSL certificates
   - Test certificate validity

4. SECRETS MANAGEMENT:
   - Generate secure secrets for all services
   - Configure environment variables
   - Verify no hardcoded secrets: search for 'password|secret|api_key|token'

5. MONITORING STACK:
   - Configure Sentry for error tracking
   - Set up health check endpoints
   - Add logging configuration

6. BACKUP & RESTORE:
   - Configure Supabase automated backups
   - Document restore procedure
   - Test backup integrity

WHEN DONE:
- Update task_plan.md: mark phaseD as complete
- Update progress.md: final summary
- mcp__memory__create_entities for deployment decisions
- /checkpoint:create 'phaseD-deployment-complete'
```

---

## Phase F: Testing & Validation (FINAL)

**Purpose**: Comprehensive testing to verify ALL success criteria. Final sign-off.
**Depends on**: Phase D
**Produces**: All tests passing, success criteria verified
**Task ID**: `phaseF`
**Assigned to**: Lead (always — final sign-off should not be delegated)

### Lead Runs Directly

```
Execute MVP_LAUNCH_CHECKLIST.md Phase F: Testing & Validation. FINAL PHASE.

Read task_plan.md, findings.md, progress.md for full context.
Read Memory: mcp__memory__read_graph() for all prior decisions and state.

COMPREHENSIVE TESTING:

1. UNIT TESTS:
   - Run: npm test (dashboard)
   - Run: uv run pytest (proxy)
   - Target: >80% code coverage per service

2. INTEGRATION TESTS:
   - Test proxy -> database integration
   - Test dashboard -> proxy integration
   - Test Stripe webhook handling
   - Test security scanning pipeline

3. END-TO-END TESTS:
   - Test user signup to first API call
   - Test budget creation to enforcement
   - Test checkout to subscription activation
   - Test security alert generation

4. LOAD TESTING:
   - Test 100 concurrent requests
   - Measure latency p50/p95/p99
   - Verify <10ms proxy overhead

5. SECURITY TESTING:
   - Verify all detectors operational
   - Test prompt injection blocking
   - Test credential detection
   - OWASP Top 10 checklist

6. SUCCESS CRITERIA CHECKLIST:

   Functional:
   - [ ] Proxy intercepts Anthropic /v1/messages
   - [ ] Proxy intercepts OpenAI /v1/chat/completions
   - [ ] Budget enforcement blocks requests when limit exceeded
   - [ ] Smart router applies cost optimization rules
   - [ ] ClawShield scans for prompt injection, secrets, malware
   - [ ] Analytics dashboard shows spend by model, provider, agent
   - [ ] Payment integration creates Stripe checkout sessions

   Infrastructure:
   - [ ] SSL/TLS on all services
   - [ ] Automated database backups
   - [ ] Sentry monitoring configured
   - [ ] Health monitoring active

   Deployment:
   - [ ] Single command deploy
   - [ ] Environment docs in .env.example
   - [ ] Setup documentation complete

   Performance:
   - [ ] Proxy latency < 10ms overhead
   - [ ] 100 concurrent requests supported
   - [ ] High availability (99.9% target)

7. FINAL CHECKPOINT:
   - mcp__memory__create_entities for test results, benchmarks, security results
   - Update progress.md with final status
   - Update task_plan.md marking all phases complete
   - /checkpoint:create 'production-ready'

DONE WHEN: ALL success criteria checkboxes verified, all tests pass, load tests meet targets, security audit clean, monitoring operational.
```

---

## Quick Reference: Execution Sequence

```
PHASE                                    TASK STATUS SIGNAL          ASSIGNED TO
──────────────────────────────────────────────────────────────────────────────────
Step 0: Bootstrap                        TaskCreate (seed)           Lead
Phase 1: Assessment                      TaskUpdate(completed)       Lead
Phase 2: Database & Migrations           TaskUpdate(completed)       database-dev
Phase 3: LLM Proxy Handler               TaskUpdate(completed)       proxy-dev
Phase 4: Budget Engine                   TaskUpdate(completed)       budget-dev
Phase 5: Smart Router                    TaskUpdate(completed)       router-dev
Phase 6: ClawShield Security (CRITICAL)  TaskUpdate(completed)       security-dev
Phase 7: Analytics & Dashboards          TaskUpdate(completed)       analytics-dev
Phase 8: Payments & Billing              TaskUpdate(completed)       payments-dev
Phase 9: Microservices Architecture      TaskUpdate(completed)       microservices-dev
Phase D: Deployment & Hardening          TaskUpdate(completed)       Lead
Phase F: Testing & Validation (FINAL)    TaskUpdate(completed)       Lead
──────────────────────────────────────────────────────────────────────────────────
                                         ALL TASKS COMPLETED → Done
```

---

## Wave Mapping (Swarm Mode)

```
┌──────────┬──────────────────────────────────────────┬────────────────┐
│  Wave    │  Phases                                  │  Mode          │
├──────────┼──────────────────────────────────────────┼────────────────┤
│  Wave 0  │  Step 0, Phase 1                         │  lead-solo     │
│  Wave 1  │  Phase 2, 3, 4, 5                        │  parallel      │
│  Wave 2  │  Phase 6, 7, 8, 9                        │  parallel      │
│  Wave 3  │  Phase D, Phase F                        │  lead-solo     │
└──────────┴──────────────────────────────────────────┴────────────────┘

Teammate count per parallel wave:
  Wave 1: 4 teammates (database-dev, proxy-dev, budget-dev, router-dev)
  Wave 2: 4 teammates (security-dev, analytics-dev, payments-dev, microservices-dev)
```

---

## File Ownership Matrix (Parallel Safety)

```
WAVE 1 TEAMMATES:
─────────────────────────────────────────────────────────────────
database-dev (Phase 2)
  Owns (exclusive edit): supabase/migrations/**, proxy/app/models/**
  Reads (shared, no edit): proxy/app/config.py, dashboard/lib/supabase.ts

proxy-dev (Phase 3)
  Owns (exclusive edit): proxy/app/core/proxy_handler.py, proxy/app/core/stream*.py
  Reads (shared, no edit): proxy/app/models/**, proxy/app/config.py

budget-dev (Phase 4)
  Owns (exclusive edit): proxy/app/core/budget_engine.py, proxy/app/api/v1/budgets.py
  Reads (shared, no edit): proxy/app/models/budget.py, supabase/migrations/**

router-dev (Phase 5)
  Owns (exclusive edit): proxy/app/core/smart_router.py, proxy/app/api/v1/routing.py
  Reads (shared, no edit): proxy/app/models/routing_rule.py, supabase/seed.sql

WAVE 2 TEAMMATES:
─────────────────────────────────────────────────────────────────
security-dev (Phase 6) - CRITICAL PATH
  Owns (exclusive edit): proxy/app/security/**, proxy/app/scanners/**
  Reads (shared, no edit): proxy/app/core/proxy_handler.py, proxy/app/models/scan.py

analytics-dev (Phase 7)
  Owns (exclusive edit): dashboard/app/analytics/**, proxy/app/api/v1/analytics.py
  Reads (shared, no edit): proxy/app/models/api_log.py, dashboard/lib/**

payments-dev (Phase 8)
  Owns (exclusive edit): dashboard/app/api/stripe/**, dashboard/app/api/webhooks/stripe/**
  Reads (shared, no edit): proxy/app/models/user.py, dashboard/lib/stripe.ts

microservices-dev (Phase 9)
  Owns (exclusive edit): services/**, docker/**, docker-compose.yml
  Reads (shared, no edit): proxy/**, dashboard/**
```

---

## Dependencies Between Phases

### Dependency Graph

```
Step 0 ─── mandatory ──→ Phase 1
Phase 1 ── mandatory ──→ Phase 2, 3, 4, 5
Phase 2 ── optional ───→ Phase 4, 5 (database for budget/router)
Phase 3 ── optional ───→ Phase 6 (proxy for security integration)
Phase 2-5 ─────────────→ Phase 6, 7, 8, 9
Phase 6-9 ─────────────→ Phase D
Phase D ───────────────→ Phase F

Critical path: Phase 6 (ClawShield Security)
Parallelizable: Phase 2-5 (Wave 1), Phase 6-9 (Wave 2)
```

---

## Agent Selection Guide

| Need | Agent / Tool |
|------|-------------|
| FastAPI implementation | `general-purpose` |
| Next.js frontend | `general-purpose` |
| Security implementation | `general-purpose` |
| Stripe integration | `general-purpose` |
| Database migrations | `general-purpose` |
| Docker configuration | `general-purpose` |
| **Team Primitives** | |
| Create team workspace | `TeamCreate(team_name=..., description=...)` |
| Create work item | `TaskCreate(subject=..., description=..., activeForm=...)` |
| Set dependencies | `TaskUpdate(taskId=..., addBlockedBy=[...])` |
| Check progress | `TaskList()` |
| Spawn teammate | `Task(subagent_type=..., team_name=..., name=..., prompt=...)` |
| Direct message | `SendMessage(type="message", recipient=..., content=...)` |
| Graceful shutdown | `SendMessage(type="shutdown_request", recipient=...)` |
| Destroy team | `TeamDelete()` |

---

## Between Phases

### Swarm Mode — Between Waves

After all teammates in a wave send completion messages:

1. **Check task list** - `TaskList()` to verify all tasks in the wave are `completed`
2. **Collect teammate findings** - Read Memory entities written by each teammate
3. **Review progress.md** - Each teammate updates this; check for conflicts or gaps
4. **Verify no file conflicts** - If teammates touched overlapping files, review diffs
5. **Resolve cross-phase issues** - If Teammate A's output affects Teammate B's work, resolve before next wave
6. **Shut down wave teammates**:
   ```
   SendMessage(type="shutdown_request", recipient="database-dev", content="Wave 1 complete.")
   SendMessage(type="shutdown_request", recipient="proxy-dev", content="Wave 1 complete.")
   SendMessage(type="shutdown_request", recipient="budget-dev", content="Wave 1 complete.")
   SendMessage(type="shutdown_request", recipient="router-dev", content="Wave 1 complete.")
   ```
   Wait for shutdown confirmations, then `TeamDelete()`
7. **Checkpoint** - `/checkpoint:create 'wave-1-complete'`
8. **Decide next** - Start next wave, or re-run failed phases with new teammates

### Handling Teammate Issues

| Symptom | Action |
|---------|--------|
| Teammate goes idle, task incomplete | `SendMessage` with guidance to continue |
| Teammate errors repeatedly | `SendMessage(shutdown_request)`, spawn replacement |
| File conflict between teammates | Pause wave, resolve manually, resume |
| Teammate drifts off-task | `SendMessage` with explicit redirect instructions |
| All teammates stuck on shared blocker | Lead investigates, broadcasts solution |

---

## Content Seeding Phase (Custom)

**Purpose**: Ensure 91 LLM model pricing data is seeded.
**Depends on**: Phase 2 (Database)
**Produces**: Complete pricing data for all providers

```
Execute Content Seeding:

1. VERIFY SEED DATA (supabase/seed.sql):
   - Check 91 model entries exist
   - Verify 16 provider coverage:
     - Anthropic, OpenAI, Google, DeepSeek
     - XAI, Mistral, Meta, Cohere
     - AI21, Amazon, Cloudflare, Groq
     - Inflection, Perplexity, Reka, Together

2. ADD MISSING ENTRIES:
   - Add any new models released in 2025-2026
   - Update pricing for existing models
   - Add input/output token costs

3. VALIDATE:
   - Run seed.sql against database
   - Verify pricing accuracy
   - Test pricing lookups in smart router
```

---

## Quality Gates Checklist

### All Phases

- [x] **Planning files read** - `Read task_plan.md, findings.md, progress.md` at START of phase
- [x] **Planning files write** - Write findings.md every 2-3 actions; update progress.md
- [x] **Decision read** - `mcp__memory__search_nodes('Decision_')` for resolved tech choices
- [x] **Implementation** - Code changes using appropriate tools
- [x] **Review** - Code review before completion
- [x] **Testing** - Tests passing for implemented features
- [x] **Planning files close** - Update task_plan.md phase status to complete
- [x] **Checkpoint** - Memory entity + `/checkpoint:create`
- [x] **Done criteria** - Clear, testable conditions met

### Swarm Mode Additions

- [x] **Task claim** - `TaskUpdate(taskId=..., owner='name', status='in_progress')` at start
- [x] **File ownership** - Phase only edits files it owns
- [x] **Task completion** - `TaskUpdate(status='completed')` when done
- [x] **Lead notification** - `SendMessage(type='message', recipient='team-lead', ...)` with summary
- [x] **Plan approval** - Teammate uses `mode='plan'` before implementing
