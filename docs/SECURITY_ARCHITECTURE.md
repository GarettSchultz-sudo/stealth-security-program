# ClawShell Runtime Protection Engine — Architecture

## Executive Summary

ClawShell Runtime Protection is a real-time security layer that intercepts, analyzes, and responds to threats as OpenClaw AI agents execute. Unlike VirusTotal (publish-time scanning) or enterprise solutions like CrowdStrike ($50K+/year), ClawShell provides accessible runtime security for individual developers and small teams.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ClawShell Runtime Protection                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐     ┌─────────────────┐     ┌──────────────────────────────┐ │
│  │ OpenClaw │────▶│  Security       │────▶│  Budget Check + Smart Route  │ │
│  │  Agent   │     │  Middleware     │     │                              │ │
│  └──────────┘     └─────────────────┘     └──────────────────────────────┘ │
│        │                  │                            │                    │
│        │                  ▼                            ▼                    │
│        │          ┌─────────────┐            ┌──────────────────┐          │
│        │          │ Detection   │            │  LLM Provider    │          │
│        │          │ Engine      │            │  (Anthropic/     │          │
│        │          └─────────────┘            │   OpenAI/etc)    │          │
│        │                  │                  └──────────────────┘          │
│        │                  ▼                            │                    │
│        │          ┌─────────────┐                     │                    │
│        │          │ Response    │◀────────────────────┘                    │
│        │          │ Scanner     │                                          │
│        │          └─────────────┘                                          │
│        │                  │                                                 │
│        ▼                  ▼                                                 │
│  ┌──────────┐     ┌─────────────┐                                          │
│  │   User   │◀────│  Response   │                                          │
│  │          │     │  Action     │                                          │
│  └──────────┘     └─────────────┘                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Request Flow with Security

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST PATH                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. CLIENT REQUEST                                                          │
│     └──▶ Authentication & Authorization                                      │
│                                                                              │
│  2. SECURITY MIDDLEWARE (SYNC <10ms)                                        │
│     └──▶ Credential Detection (secrets, API keys)                           │
│     └──▶ Prompt Injection Detection (signatures + heuristics)               │
│     └──▶ PII Detection (SSN, credit cards, etc.)                            │
│     └──▶ Tool Policy Check (allowed/denied tools)                           │
│                                                                              │
│  3. BUDGET CHECK                                                            │
│     └──▶ Budget Engine (existing)                                           │
│                                                                              │
│  4. SMART ROUTING                                                           │
│     └──▶ Smart Router (existing)                                            │
│                                                                              │
│  5. PROVIDER API                                                            │
│     └──▶ Forward to LLM provider                                            │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                              RESPONSE PATH                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  6. RESPONSE SCANNER (ASYNC)                                                │
│     └──▶ Data Exfiltration Detection                                        │
│     └──▶ Secret Exposure in Output                                          │
│     └──▶ Behavioral Anomaly Update                                          │
│                                                                              │
│  7. STREAMING RESPONSE                                                      │
│     └──▶ Real-time stream to client                                         │
│     └──▶ Kill switch can terminate mid-stream                               │
│                                                                              │
│  8. LOGGING & TELEMETRY                                                     │
│     └──▶ Cost calculation (existing)                                        │
│     └──▶ Security event logging                                             │
│     └──▶ Baseline updates                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detection Categories

### 1. Prompt Injection Detection (LLM01:2025)

**Detection Layers:**
- **Signature-based**: Known injection patterns, jailbreak templates
- **Heuristic-based**: Instruction override patterns, delimiter abuse
- **Semantic-based**: Embedding similarity to injection corpus
- **Structural-based**: Token anomalies, encoding attacks

**Patterns Detected:**
- System prompt override attempts
- Role-play jailbreaks ("you are now DAN")
- Delimiter injection (```, """, XML tag injection)
- Base64/Unicode encoded instructions
- Indirect injection via fetched content
- Multi-turn gradual context manipulation

### 2. Data Exfiltration Detection

**Detection Types:**
- PII patterns (SSN, credit cards, passport, email, phone)
- Credential patterns (50+ API key formats)
- High-entropy string detection
- Outbound data volume anomalies
- Encoding-based exfiltration (base64, hex)
- DNS tunneling patterns

### 3. Behavioral Anomaly Detection

**Baseline Metrics:**
- API calls per minute/hour/day
- Token consumption rate
- Unique models accessed
- Tool invocation frequency and types
- Conversation length distribution
- Time-of-day activity patterns
- Error rate and retry patterns
- New skill activation frequency

**Anomaly Detection:**
- Z-score based deviation from baseline
- Composite anomaly scoring
- Adaptive thresholds with feedback learning

### 4. Tool Abuse Detection

**Patterns Detected:**
- Unauthorized tool usage
- Privilege escalation attempts
- Shell injection (rm -rf, curl | bash)
- Sensitive file access (/etc/shadow, ~/.ssh)
- Network abuse (malicious IPs/domains)
- Browser exploitation patterns

### 5. Runaway Loop Detection

**Detection:**
- >N API calls in M seconds with similar content
- Projected spend exceeding budget at current rate
- Infinite retry patterns

### 6. Credential Exposure Detection

**Patterns:**
- 50+ credential patterns (AWS, GitHub, Stripe, JWT, etc.)
- Entropy-based unknown secret detection
- Context-aware detection (code block vs natural language)
- Bidirectional (request AND response)

### 7. Runtime Skill Scanner

**Analysis:**
- Skill behavior profiling
- Drift detection from baseline
- Permission violation detection
- Unexpected network callouts
- Data flow tracking

## Response Actions

| Action | Description | Latency Impact |
|--------|-------------|----------------|
| LOG | Record event, no user impact | None |
| ALERT | Real-time notification | None |
| WARN | Insert warning in response | Minimal |
| THROTTLE | Rate-limit API calls | Variable |
| DOWNGRADE | Force cheaper/safer model | Minimal |
| BLOCK | Reject request, return error | Immediate |
| QUARANTINE | Block + save for review | Immediate |
| KILL | Terminate all agent connections | Immediate |

## Latency Budget

| Stage | Budget | Notes |
|-------|--------|-------|
| Sync Detection | <10ms | Pattern matching, credential detection |
| Total Middleware | <50ms p99 | Including budget + routing |
| Async Detection | Background | Behavioral analysis, VT lookup |
| Event Streaming | <1s | Dashboard notification delivery |

## Database Schema (New Tables)

### security_events
```sql
CREATE TABLE security_events (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  agent_id UUID,
  skill_id UUID,
  event_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL, -- critical, high, medium, low, info
  confidence_score DECIMAL(3,2),
  detection_source VARCHAR(50),
  rule_id UUID,
  request_summary TEXT,
  response_summary TEXT,
  action_taken VARCHAR(20),
  action_details JSONB,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### detection_rules
```sql
CREATE TABLE detection_rules (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  rule_type VARCHAR(50), -- pattern, threshold, behavioral, composite
  rule_definition JSONB NOT NULL,
  severity VARCHAR(20) DEFAULT 'medium',
  enabled BOOLEAN DEFAULT true,
  action VARCHAR(20) DEFAULT 'alert',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### agent_baselines
```sql
CREATE TABLE agent_baselines (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  agent_id UUID NOT NULL,
  metric_name VARCHAR(100) NOT NULL,
  metric_value DECIMAL(20,6),
  baseline_mean DECIMAL(20,6),
  baseline_stddev DECIMAL(20,6),
  sample_count INTEGER,
  window_start TIMESTAMPTZ,
  window_end TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(org_id, agent_id, metric_name)
);
```

### agent_security_policies
```sql
CREATE TABLE agent_security_policies (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  agent_id UUID NOT NULL UNIQUE,
  detection_level VARCHAR(20) DEFAULT 'monitor', -- monitor, warn, enforce
  tool_allowlist JSONB,
  tool_denylist JSONB,
  auto_kill_enabled BOOLEAN DEFAULT false,
  auto_kill_threshold INTEGER DEFAULT 100,
  notification_config JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### quarantined_requests
```sql
CREATE TABLE quarantined_requests (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  agent_id UUID,
  request_body_encrypted TEXT,
  detection_reasons JSONB,
  status VARCHAR(20) DEFAULT 'pending_review',
  reviewed_by UUID,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### threat_iocs
```sql
CREATE TABLE threat_iocs (
  id UUID PRIMARY KEY,
  ioc_type VARCHAR(20), -- ip, domain, hash, pattern
  ioc_value TEXT NOT NULL,
  source VARCHAR(100),
  severity VARCHAR(20) DEFAULT 'medium',
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

### Security Dashboard
- `GET /api/security/overview` - Threat summary, scores, recent events
- `GET /api/security/events` - Paginated security events with filters
- `GET /api/security/events/:id` - Single event detail
- `POST /api/security/events/:id/dismiss` - Dismiss false positive
- `WS /api/security/stream` - WebSocket for live events

### Detection Rules
- `GET /api/security/rules` - List all rules
- `POST /api/security/rules` - Create custom rule
- `PUT /api/security/rules/:id` - Update rule
- `DELETE /api/security/rules/:id` - Delete custom rule
- `POST /api/security/rules/test` - Test rule against sample

### Agent Security
- `GET /api/security/agents/:id/policy` - Get agent security policy
- `PUT /api/security/agents/:id/policy` - Update agent policy
- `GET /api/security/agents/:id/baseline` - Get behavioral baseline
- `POST /api/security/agents/:id/kill` - KILL SWITCH
- `POST /api/security/agents/:id/resume` - Resume after kill

### Quarantine
- `GET /api/security/quarantine` - List quarantined requests
- `POST /api/security/quarantine/:id/approve` - Release request
- `POST /api/security/quarantine/:id/reject` - Permanently block

## Module Structure

```
proxy/app/security/
├── __init__.py
├── engine.py              # Main SecurityEngine orchestrator
├── models.py              # Pydantic models for threats, alerts
├── config.py              # Security configuration & thresholds
├── middleware.py          # FastAPI middleware integration
├── detectors/
│   ├── __init__.py
│   ├── base.py            # Abstract BaseDetector class
│   ├── prompt_injection.py
│   ├── data_exfil.py
│   ├── anomaly.py
│   ├── credential.py
│   ├── runaway.py
│   ├── tool_abuse.py
│   └── skill_scanner.py
├── rules/
│   ├── __init__.py
│   ├── engine.py          # Rule matching engine
│   ├── loader.py          # Load rules from DB + filesystem
│   └── builtin/           # Built-in detection rules (YAML)
├── response/
│   ├── __init__.py
│   ├── actions.py         # Alert, Block, Downgrade, Kill actions
│   ├── kill_switch.py     # Emergency agent termination
│   └── quarantine.py      # Request quarantine & replay
├── intel/
│   ├── __init__.py
│   ├── threat_feeds.py    # External threat intelligence
│   ├── ioc_database.py    # Indicators of Compromise DB
│   └── virustotal.py      # VirusTotal API integration
└── telemetry/
    ├── __init__.py
    ├── collector.py       # Event collection & normalization
    ├── stream.py          # Real-time event streaming
    └── baseline.py        # Behavioral baseline computation
```

## References

- [OWASP Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Prompt_Injection_Cheat_Sheet.html)
- [Acuvity AI Runtime Security](https://acuvity.ai/ai-runtime-security/)
- [Obsidian Security - AI Agent Security Risks](https://www.obsidiansecurity.com/blog/ai-agent-security-risks)
