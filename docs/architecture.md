# ClawShell Runtime Protection Engine - Architecture Design

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Date | 2026-02-15 |
| Classification | Internal |
| Status | Draft |

---

## 1. System Overview

### 1.1 Purpose

ClawShell is a security middleware layer that provides real-time threat detection and response for AI agent communications with LLM APIs. It operates as a transparent proxy, analyzing all traffic for security threats.

### 1.2 Design Principles

| Principle | Description |
|-----------|-------------|
| **Defense in Depth** | Multiple layers of detection (6 detectors) |
| **Fail Safe** | Default deny for critical threats |
| **Low Latency** | <10ms synchronous detection budget |
| **Observability** | Full audit trail of all security events |
| **Extensibility** | Plugin architecture for custom detectors |
| **Scalability** | Horizontal scaling via stateless design |

### 1.3 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ClawShell System                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌─────────────┐                                                          │
│    │   Client    │                                                          │
│    │  (AI Agent) │                                                          │
│    └──────┬──────┘                                                          │
│           │                                                                  │
│           ▼                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │                         API Gateway                                  │  │
│    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │  │
│    │  │    Auth     │  │ Rate Limit  │  │   Routing   │                 │  │
│    │  └─────────────┘  └─────────────┘  └─────────────┘                 │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│           │                                                                  │
│           ▼                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │                     Security Middleware Layer                        │  │
│    │                                                                      │  │
│    │  ┌───────────────────────────────────────────────────────────────┐  │  │
│    │  │                    Security Engine                             │  │  │
│    │  │                                                                │  │  │
│    │  │   ┌─────────────────────────────────────────────────────┐    │  │  │
│    │  │   │              Detection Pipeline                      │    │  │  │
│    │  │   │                                                     │    │  │  │
│    │  │   │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │    │  │  │
│    │  │   │  │Cred │ │Prompt│ │Tool │ │Exfil│ │Run  │ │Anom │  │    │  │  │
│    │  │   │  │ P:5 │ │ P:10│ │ P:10│ │ P:15│ │ P:20│ │ P:50│  │    │  │  │
│    │  │   │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │    │  │  │
│    │  │   │                                                     │    │  │  │
│    │  │   └─────────────────────────────────────────────────────┘    │  │  │
│    │  │                           │                                   │  │  │
│    │  │                           ▼                                   │  │  │
│    │  │   ┌─────────────────────────────────────────────────────┐    │  │  │
│    │  │   │              Action Determination                    │    │  │  │
│    │  │   │                                                     │    │  │  │
│    │  │   │   LOG → ALERT → WARN → THROTTLE → BLOCK → KILL     │    │  │  │
│    │  │   │                                                     │    │  │  │
│    │  │   └─────────────────────────────────────────────────────┘    │  │  │
│    │  │                                                                │  │  │
│    │  └───────────────────────────────────────────────────────────────┘  │  │
│    │                                                                      │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│           │                                                                  │
│           ▼                                                                  │
│    ┌─────────────┐                                                          │
│    │   LLM API   │                                                          │
│    │ (Upstream)  │                                                          │
│    └─────────────┘                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Core Components

#### 2.1.1 Security Engine

**File:** `proxy/app/security/engine.py`

```python
class SecurityEngine:
    """
    Central orchestrator for runtime protection.

    Responsibilities:
    - Coordinate detector execution
    - Manage detector lifecycle
    - Determine response actions
    - Emit security events
    - Manage policies and threat indicators
    """
```

**Key Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| `_detectors` | list[BaseDetector] | All registered detectors |
| `_sync_detectors` | list[SyncDetector] | Synchronous detectors |
| `_async_detectors` | list[AsyncDetector] | Asynchronous detectors |
| `_policies` | dict[str, AgentSecurityPolicy] | Agent security policies |
| `_threat_indicators` | dict[str, ThreatIndicator] | IOC cache |
| `_action_handlers` | dict[ResponseAction, Callable] | Action callbacks |
| `_executor` | ThreadPoolExecutor | Thread pool for sync detectors |

**Key Methods:**
| Method | Description |
|--------|-------------|
| `analyze_request()` | Run all detectors on request |
| `analyze_response()` | Run all detectors on response |
| `take_actions()` | Execute required actions |
| `_determine_actions()` | Map detections to actions |

#### 2.1.2 Security Middleware

**File:** `proxy/app/security/middleware.py`

```python
class SecurityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request/response interception.

    Responsibilities:
    - Intercept HTTP requests
    - Route to security engine
    - Handle block responses
    - Support streaming analysis
    """
```

**Protected Paths:**
```python
paths_to_protect = [
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/messages",
    "/v1/embeddings",
    "/api/agent/",
]
```

**Excluded Paths:**
```python
excluded_paths = [
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
]
```

#### 2.1.3 Detection Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Detection Pipeline                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Request/Response                                                           │
│         │                                                                    │
│         ▼                                                                    │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                      Priority Queue                                    │ │
│   │                                                                        │ │
│   │   Priority 5:  CredentialDetector     (catch secrets early)          │ │
│   │   Priority 10: PromptInjectionDetector (injection patterns)          │ │
│   │   Priority 10: ToolAbuseDetector       (dangerous commands)          │ │
│   │   Priority 15: DataExfiltrationDetector (PII/volume)                 │ │
│   │   Priority 20: RunawayDetector         (rate/loop detection)         │ │
│   │   Priority 50: AnomalyDetector         (statistical analysis)        │ │
│   │                                                                        │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│         │                                                                    │
│         ▼                                                                    │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                    Result Aggregation                                  │ │
│   │                                                                        │ │
│   │   - Collect all DetectionResult objects                               │ │
│   │   - Determine max severity                                            │ │
│   │   - Calculate max confidence                                          │ │
│   │   - Identify all threat types                                         │ │
│   │                                                                        │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│         │                                                                    │
│         ▼                                                                    │
│   DetectionSummary                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Detector Architecture

#### 2.2.1 Base Detector Classes

```
┌─────────────────────────────────────────────────────────────────┐
│                        BaseDetector (ABC)                        │
│                                                                  │
│  + name: str                                                     │
│  + threat_type: ThreatType                                       │
│  + priority: int                                                 │
│  + enabled: bool                                                 │
│                                                                  │
│  + detect_request() -> list[DetectionResult]                    │
│  + detect_response() -> list[DetectionResult]                   │
│  + _create_result() -> DetectionResult                          │
│                                                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐     ┌───────────────────────┐
│    SyncDetector       │     │    AsyncDetector      │
│                       │     │                       │
│  Runs in <10ms        │     │  Background tasks     │
│  Thread pool executor │     │  Can kill streams     │
│                       │     │                       │
│  + detect_request_    │     │  + can_kill_stream    │
│    sync()             │     │                       │
│  + detect_response_   │     │                       │
│    sync()             │     │                       │
└───────────────────────┘     └───────────────────────┘
```

#### 2.2.2 Detector Implementations

| Detector | Priority | Type | Latency | Description |
|----------|----------|------|---------|-------------|
| CredentialDetector | 5 | Sync | ~2ms | Pattern + entropy analysis |
| PromptInjectionDetector | 10 | Sync | ~3ms | Signature + heuristic matching |
| ToolAbuseDetector | 10 | Sync | ~2ms | Command + path patterns |
| DataExfiltrationDetector | 15 | Sync | ~3ms | PII + volume detection |
| RunawayDetector | 20 | Sync | ~1ms | Rate + similarity tracking |
| AnomalyDetector | 50 | Sync | ~2ms | Statistical z-score analysis |

#### 2.2.3 Detector Configuration

```python
@dataclass
class DetectorConfig:
    """Configuration for individual detectors."""
    enabled: bool = True
    priority: int = 100
    custom_patterns: list[str] = field(default_factory=list)
    thresholds: dict[str, float] = field(default_factory=dict)
```

---

### 2.3 Data Models

#### 2.3.1 Core Models

```
┌─────────────────────────────────────────────────────────────────┐
│                      DetectionResult                             │
├─────────────────────────────────────────────────────────────────┤
│  detected: bool                                                  │
│  threat_type: ThreatType                                         │
│  severity: SeverityLevel                                         │
│  confidence: Decimal (0-1)                                       │
│  source: DetectionSource                                         │
│  description: str                                                │
│  evidence: dict[str, Any]                                        │
│  rule_id: str | None                                             │
│  metadata: dict[str, Any]                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       SecurityEvent                              │
├─────────────────────────────────────────────────────────────────┤
│  id: UUID                                                        │
│  org_id: UUID | None                                             │
│  agent_id: UUID | None                                           │
│  request_id: UUID | None                                         │
│  threat_type: ThreatType                                         │
│  severity: SeverityLevel                                         │
│  confidence: Decimal                                             │
│  source: DetectionSource                                         │
│  description: str                                                │
│  evidence: dict[str, Any]                                        │
│  action_taken: ResponseAction                                    │
│  action_details: dict[str, Any]                                  │
│  created_at: datetime                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   AgentSecurityPolicy                            │
├─────────────────────────────────────────────────────────────────┤
│  agent_id: UUID                                                  │
│  org_id: UUID                                                    │
│  detection_level: str  # monitor, warn, enforce                  │
│  tool_allowlist: list[str]                                       │
│  tool_denylist: list[str]                                        │
│  auto_kill_enabled: bool                                         │
│  auto_kill_threshold: int                                        │
│  notify_on_critical: bool                                        │
│  notify_on_high: bool                                            │
│  notification_channels: list[str]                                │
│  rate_limit_per_minute: int | None                               │
│  max_tokens_per_request: int | None                              │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.2 Enumerations

```python
class ThreatType(str, enum.Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_EXPOSURE = "credential_exposure"
    TOOL_ABUSE = "tool_abuse"
    RUNAWAY_LOOP = "runaway_loop"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    SKILL_VIOLATION = "skill_violation"
    NETWORK_ABUSE = "network_abuse"
    PII_EXPOSURE = "pii_exposure"
    CUSTOM = "custom"

class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ResponseAction(str, enum.Enum):
    LOG = "log"
    ALERT = "alert"
    WARN = "warn"
    THROTTLE = "throttle"
    DOWNGRADE = "downgrade"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    KILL = "kill"
    REDACT = "redact"

class DetectionSource(str, enum.Enum):
    SIGNATURE = "signature"
    HEURISTIC = "heuristic"
    BEHAVIORAL = "behavioral"
    SEMANTIC = "semantic"
    EXTERNAL = "external"
    USER_REPORT = "user_report"
```

---

## 3. Request Flow

### 3.1 Synchronous Request Flow

```
┌──────────┐     ┌───────────┐     ┌───────────┐     ┌──────────┐
│  Client  │────▶│ Middleware│────▶│  Engine   │────▶│ Detector │
│ Request  │     │  (parse)  │     │ (analyze) │     │ Pipeline │
└──────────┘     └───────────┘     └───────────┘     └──────────┘
      │                │                 │                 │
      │                │                 │                 │
      │                │                 │                 ▼
      │                │                 │          ┌─────────────┐
      │                │                 │          │   Results   │
      │                │                 │          │ Aggregation │
      │                │                 │          └─────────────┘
      │                │                 │                 │
      │                │                 │                 │
      │                │                 ▼                 │
      │                │          ┌─────────────┐         │
      │                │          │   Action    │◀────────┘
      │                │          │Determination│
      │                │          └─────────────┘
      │                │                 │
      │                │                 │
      │                │        ┌────────┴────────┐
      │                │        │                 │
      │                │        ▼                 ▼
      │                │  ┌───────────┐    ┌───────────┐
      │                │  │   ALLOW   │    │   BLOCK   │
      │                │  └─────┬─────┘    └─────┬─────┘
      │                │        │                │
      │                │        │                │
      │                │        ▼                ▼
      │                │  ┌───────────┐    ┌───────────┐
      │                │  │  LLM API  │    │  403 Resp │
      │                │  └─────┬─────┘    └───────────┘
      │                │        │                │
      │                │        │                │
      │                │        ▼                │
      │                │  ┌───────────┐          │
      │                │  │  Response │          │
      │                │  │  Analysis │          │
      │                │  └─────┬─────┘          │
      │                │        │                │
      │                │        │                │
      │◀───────────────┴────────┴────────────────┘
      │
      ▼
┌──────────┐
│  Client  │
│ Response │
└──────────┘
```

### 3.2 Streaming Response Flow

```
┌──────────┐     ┌───────────┐     ┌───────────┐
│  LLM API │────▶│ Streaming │────▶│  Security │
│  Stream  │     │Interceptor│     │  Analysis │
└──────────┘     └───────────┘     └───────────┘
      │                │                 │
      │                │                 │
      │                │                 ▼
      │                │          ┌─────────────┐
      │                │          │   Buffer    │
      │                │          │  (1000 ch)  │
      │                │          └─────────────┘
      │                │                 │
      │                │                 │
      │                │                 ▼
      │                │          ┌─────────────┐
      │                │          │   Threat    │
      │                │          │   Check     │
      │                │          └─────────────┘
      │                │                 │
      │                │          ┌──────┴──────┐
      │                │          │             │
      │                │          ▼             ▼
      │                │    ┌──────────┐ ┌──────────┐
      │                │    │  ALLOW   │ │   KILL   │
      │                │    │  chunk   │ │  stream  │
      │                │    └────┬─────┘ └──────────┘
      │                │         │
      │                │         │
      │◀───────────────┴─────────┘
      │
      ▼
┌──────────┐
│  Client  │
│  Chunk   │
└──────────┘
```

---

## 4. Deployment Architecture

### 4.1 Production Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                           VPC                                        │    │
│  │                                                                      │    │
│  │   ┌─────────────────────────────────────────────────────────────┐   │    │
│  │   │                    Public Subnet                             │   │    │
│  │   │                                                              │   │    │
│  │   │   ┌─────────────┐      ┌─────────────┐                      │   │    │
│  │   │   │     ALB     │      │   NAT GW    │                      │   │    │
│  │   │   │ (Load Bal.) │      │             │                      │   │    │
│  │   │   └──────┬──────┘      └─────────────┘                      │   │    │
│  │   │          │                                                   │   │    │
│  │   └──────────┼───────────────────────────────────────────────────┘   │    │
│  │              │                                                         │
│  │   ┌──────────┼───────────────────────────────────────────────────┐   │    │
│  │   │          ▼           Private Subnet                           │   │    │
│  │   │   ┌─────────────────────────────────────────────────────┐    │   │    │
│  │   │   │              ECS Fargate Cluster                     │    │   │    │
│  │   │   │                                                      │    │   │    │
│  │   │   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │   │    │
│  │   │   │   │  ClawShell  │  │  ClawShell  │  │  ClawShell  │ │    │   │    │
│  │   │   │   │  Service 1  │  │  Service 2  │  │  Service N  │ │    │   │    │
│  │   │   │   │  (proxy)    │  │  (proxy)    │  │  (proxy)    │ │    │   │    │
│  │   │   │   └─────────────┘  └─────────────┘  └─────────────┘ │    │   │    │
│  │   │   │                                                      │    │   │    │
│  │   │   └─────────────────────────────────────────────────────┘    │   │    │
│  │   │                                                              │   │    │
│  │   │   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │   │    │
│  │   │   │     RDS     │      │    Redis    │      │   S3 Bucket │ │   │    │
│  │   │   │ (PostgreSQL)│      │  (ElastiC)  │      │  (Reports)  │ │   │    │
│  │   │   └─────────────┘      └─────────────┘      └─────────────┘ │   │    │
│  │   │                                                              │   │    │
│  │   └──────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Shared Services                                   │   │
│   │                                                                      │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│   │   │ CloudWatch  │  │   Secrets   │  │   SQS       │                 │   │
│   │   │  (Logging)  │  │  Manager    │  │  (Queue)    │                 │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Container Architecture

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy application
COPY app/ ./app/

# Run with gunicorn for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

### 4.3 Scaling Strategy

| Metric | Scale Trigger | Action |
|--------|---------------|--------|
| CPU > 70% | Add ECS tasks | Horizontal scale out |
| Request latency > 100ms | Add ECS tasks | Horizontal scale out |
| Active connections > 1000/task | Add ECS tasks | Connection scaling |
| Queue depth > 100 | Add workers | Async processing |

---

## 5. Data Architecture

### 5.1 Database Schema

```sql
-- Security Events
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    agent_id UUID REFERENCES agents(id),
    request_id UUID,

    -- Detection details
    threat_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    source VARCHAR(20) NOT NULL,

    -- Content
    description TEXT NOT NULL,
    evidence JSONB,

    -- Response
    action_taken VARCHAR(20) NOT NULL,
    action_details JSONB,

    -- Metadata
    rule_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_org_created ON security_events(org_id, created_at DESC);
CREATE INDEX idx_events_agent ON security_events(agent_id);
CREATE INDEX idx_events_severity ON security_events(severity);

-- Security Policies
CREATE TABLE security_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) UNIQUE,
    org_id UUID REFERENCES organizations(id),

    detection_level VARCHAR(20) DEFAULT 'monitor',
    auto_kill_enabled BOOLEAN DEFAULT FALSE,
    auto_kill_threshold INTEGER DEFAULT 95,

    tool_allowlist TEXT[],
    tool_denylist TEXT[],

    rate_limit_per_minute INTEGER,
    max_tokens_per_request INTEGER,

    notify_on_critical BOOLEAN DEFAULT TRUE,
    notify_on_high BOOLEAN DEFAULT TRUE,
    notification_channels TEXT[] DEFAULT ARRAY['dashboard'],

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Quarantined Requests
CREATE TABLE quarantined_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    agent_id UUID REFERENCES agents(id),

    request_body_encrypted TEXT NOT NULL,
    detection_reasons JSONB NOT NULL,

    status VARCHAR(20) DEFAULT 'pending_review',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Threat Indicators (IOCs)
CREATE TABLE threat_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ioc_type VARCHAR(50) NOT NULL,
    ioc_value TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    threat_types TEXT[],
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_indicators_value ON threat_indicators(ioc_value);
CREATE INDEX idx_indicators_type ON threat_indicators(ioc_type);
```

### 5.2 Redis Cache Schema

```
# Rate Limiting
ratelimit:{agent_id}:{minute}     -> count (TTL: 60s)
ratelimit:{agent_id}:{hour}       -> count (TTL: 3600s)

# Behavioral Baselines
baseline:{agent_id}:input_tokens  -> {mean, stddev, count}
baseline:{agent_id}:output_tokens -> {mean, stddev, count}
baseline:{agent_id}:request_size  -> {mean, stddev, count}

# Threat Indicator Cache
threat:ioc:{hash}                 -> indicator_json (TTL: 3600s)

# Session State
session:{session_id}              -> {agent_id, user_id, created_at}
```

---

## 6. API Design

### 6.1 Security Status API

```yaml
GET /security/status
  Response:
    {
      "enabled": true,
      "detection_level": "monitor",
      "detectors": {
        "credential_detector": {"enabled": true, "priority": 5},
        "prompt_injection_detector": {"enabled": true, "priority": 10},
        ...
      }
    }

GET /security/events
  Parameters:
    - org_id: UUID
    - agent_id: UUID
    - severity: critical|high|medium|low
    - threat_type: string
    - from: datetime
    - to: datetime
    - limit: int (default: 100)
  Response:
    {
      "events": [...],
      "total": 1234,
      "page": 1
    }

POST /security/policies
  Body:
    {
      "agent_id": "uuid",
      "detection_level": "enforce",
      "auto_kill_enabled": true,
      "rate_limit_per_minute": 60
    }

PUT /security/policies/{agent_id}
  Body:
    {
      "detection_level": "warn"
    }

POST /security/indicators
  Body:
    {
      "ioc_type": "domain",
      "ioc_value": "malicious.example.com",
      "severity": "high",
      "threat_types": ["prompt_injection"]
    }
```

### 6.2 Webhook Notifications

```yaml
POST {webhook_url}
  Headers:
    X-Signature: sha256={hmac}
    X-Event-Type: security.alert
  Body:
    {
      "event_id": "uuid",
      "timestamp": "2026-02-15T12:00:00Z",
      "org_id": "uuid",
      "agent_id": "uuid",
      "threat_type": "prompt_injection",
      "severity": "critical",
      "confidence": 0.95,
      "action_taken": "block",
      "description": "Critical prompt injection detected"
    }
```

---

## 7. Security Considerations

### 7.1 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Request                                                        │
│      │                                                           │
│      ▼                                                           │
│   ┌─────────────────┐                                           │
│   │  API Key Check  │──▶ Invalid ──▶ 401 Unauthorized           │
│   └────────┬────────┘                                           │
│            │ Valid                                               │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │  Org Lookup     │──▶ Not Found ──▶ 401 Unauthorized         │
│   └────────┬────────┘                                           │
│            │ Found                                               │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │  Policy Check   │──▶ No Policy ──▶ Use Default Policy       │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │  Security       │                                           │
│   │  Analysis       │                                           │
│   └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Protection

| Data Type | At Rest | In Transit | Retention |
|-----------|---------|------------|-----------|
| API Keys | AES-256-GCM | TLS 1.3 | 0 days |
| PII | AES-256-GCM | TLS 1.3 | 90 days |
| Security Events | AES-256-GCM | TLS 1.3 | 90 days |
| Request Logs | None | TLS 1.3 | 30 days |
| Quarantined Data | AES-256-GCM | TLS 1.3 | 7 days |

### 7.3 Secrets Management

```yaml
AWS Secrets Manager:
  - /clawshell/db/credentials
  - /clawshell/redis/credentials
  - /clawshell/llm/api_keys
  - /clawshell/encryption/keys

Environment Variables (ECS):
  - AWS_REGION
  - LOG_LEVEL
  - SECURITY_DETECTION_LEVEL
```

---

## 8. Performance Requirements

### 8.1 Latency Budgets

| Operation | Budget | Actual | Margin |
|-----------|--------|--------|--------|
| Request Parsing | 1ms | 0.5ms | 50% |
| Credential Detection | 2ms | 1.5ms | 25% |
| Prompt Injection Detection | 3ms | 2.5ms | 17% |
| Tool Abuse Detection | 2ms | 1.5ms | 25% |
| Data Exfil Detection | 3ms | 2.5ms | 17% |
| Runaway Detection | 1ms | 0.5ms | 50% |
| Anomaly Detection | 2ms | 1.5ms | 25% |
| Action Determination | 1ms | 0.5ms | 50% |
| **Total** | **15ms** | **10.5ms** | **30%** |

### 8.2 Throughput Requirements

| Metric | Target | Peak |
|--------|--------|------|
| Requests/second | 1,000 | 5,000 |
| Concurrent connections | 10,000 | 50,000 |
| Events/second | 10,000 | 50,000 |

### 8.3 Resource Allocation

```yaml
ECS Task Definition:
  CPU: 1 vCPU
  Memory: 2 GB

  Limits:
    cpu_reservation: 512
    memory_reservation: 1 GB

  Auto-scaling:
    min_tasks: 2
    max_tasks: 20
    target_cpu: 70
```

---

## 9. Monitoring & Observability

### 9.1 Metrics

```yaml
CloudWatch Metrics:
  - ClawShell/Requests/Total
  - ClawShell/Requests/Blocked
  - ClawShell/Requests/Latency
  - ClawShell/Detections/{type}
  - ClawShell/Actions/{action}
  - ClawShell/Errors/Total

Custom Metrics:
  - Detection latency by detector
  - False positive rate
  - Threat severity distribution
```

### 9.2 Logging

```python
# Structured logging format
{
    "timestamp": "2026-02-15T12:00:00.000Z",
    "level": "INFO",
    "service": "clawshell-proxy",
    "request_id": "uuid",
    "org_id": "uuid",
    "agent_id": "uuid",
    "event_type": "security_detection",
    "threat_type": "prompt_injection",
    "severity": "high",
    "confidence": 0.85,
    "action": "block",
    "latency_ms": 12.5
}
```

### 9.3 Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Block Rate | > 10% blocks | Warning |
| Critical Detection | Any critical threat | Critical |
| Detection Latency | > 20ms p99 | Warning |
| Error Rate | > 1% errors | Warning |
| Service Unavailable | Health check fail | Critical |

---

## 10. Future Enhancements

### Phase 1 (Current)
- ✅ 6 synchronous detectors
- ✅ FastAPI middleware integration
- ✅ Basic action handlers

### Phase 2 (Planned)
- ⬜ ML-based semantic analysis
- ⬜ Async detector framework
- ⬜ Real-time dashboard
- ⬜ Custom rule engine

### Phase 3 (Future)
- ⬜ Multi-tenant isolation
- ⬜ Compliance reporting
- ⬜ Threat intelligence feeds
- ⬜ Honeypot detection

---

## Appendix A: File Structure

```
proxy/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── config.py                  # Application configuration
│   │
│   ├── security/
│   │   ├── __init__.py           # Public API exports
│   │   ├── engine.py             # SecurityEngine orchestrator
│   │   ├── middleware.py         # FastAPI middleware
│   │   ├── models.py             # Pydantic models
│   │   ├── config.py             # Security configuration
│   │   │
│   │   └── detectors/
│   │       ├── __init__.py       # Detector exports
│   │       ├── base.py           # Base detector classes
│   │       ├── prompt_injection.py
│   │       ├── credential.py
│   │       ├── data_exfil.py
│   │       ├── runaway.py
│   │       ├── tool_abuse.py
│   │       └── anomaly.py
│   │
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   │       ├── agents.py
│   │       ├── analytics.py
│   │       └── ...
│   │
│   └── models/
│       ├── database.py
│       ├── agent.py
│       └── scan.py
│
├── tests/
│   └── test_security_engine.py
│
├── pyproject.toml
└── Dockerfile
```

---

## Appendix B: Configuration Reference

```yaml
# Environment Variables

# Application
APP_ENV: development | production
LOG_LEVEL: DEBUG | INFO | WARNING | ERROR

# Database
DATABASE_URL: postgresql+asyncpg://...
REDIS_URL: redis://...

# Security Engine
SECURITY_ENABLED: true | false
SECURITY_DETECTION_LEVEL: monitor | warn | enforce
SECURITY_AUTO_KILL: true | false
SECURITY_AUTO_KILL_THRESHOLD: 0.95

# Latency
MAX_SYNC_DETECTION_MS: 10
MAX_TOTAL_MIDDLEWARE_MS: 50

# External APIs
VIRUSTOTAL_API_KEY: (optional)
ABUSEIPDB_API_KEY: (optional)
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | ClawShell Team | Initial architecture design |
