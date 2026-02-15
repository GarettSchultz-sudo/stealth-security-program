# ClawShell Threat Model

## Overview

This document outlines the security threats specific to AI agents operating through the ClawShell proxy, mapped to detection capabilities and response actions.

## STRIDE Classification

| Threat Category | STRIDE | Description | ClawShell Detection |
|-----------------|--------|-------------|---------------------|
| Prompt Injection | Tampering | Malicious prompts alter agent behavior | ✅ Prompt Injection Detector |
| Data Exfiltration | Information Disclosure | Sensitive data leaves via agent | ✅ Data Exfil Detector |
| Credential Theft | Information Disclosure | Secrets exposed to agent/LLM | ✅ Credential Detector |
| Runaway Loops | Denial of Service | Infinite API calls drain budget | ✅ Runaway Detector |
| Privilege Escalation | Elevation of Privilege | Agent gains unauthorized access | ✅ Tool Abuse Detector |
| Supply Chain | Tampering | Malicious skills compromise agent | ✅ Skill Scanner |
| Memory Poisoning | Tampering | Corrupted context influences behavior | ✅ Anomaly Detector |

## Threat Categories

### 1. Prompt Injection (Critical)

**Attack Vectors:**
- Direct injection via user messages
- Indirect injection via fetched content
- Multi-turn gradual injection
- Tool output injection
- System prompt extraction

**Detection Opportunities at Proxy:**
- Request body contains known injection patterns
- Unusual token sequences
- System prompt override attempts
- Role manipulation patterns

**Risk Rating:** High likelihood × High impact = **Critical**

### 2. Data Exfiltration (Critical)

**Attack Vectors:**
- Agent leaks PII in responses
- Secrets included in conversation
- Large data volume extraction
- Encoded data smuggling (base64, hex)
- DNS tunneling via tool calls

**Detection Opportunities at Proxy:**
- Response contains PII patterns
- High-entropy strings in output
- Unusual data volume
- Encoding anomalies

**Risk Rating:** Medium likelihood × High impact = **Critical**

### 3. Credential Theft (High)

**Attack Vectors:**
- Secrets in request messages
- Agent outputs environment variables
- Tool responses contain credentials
- Memory/state leakage

**Detection Opportunities at Proxy:**
- Request contains API keys, tokens
- Response contains credential patterns
- Entropy analysis for unknown secrets

**Risk Rating:** Medium likelihood × High impact = **High**

### 4. Runaway Agent / Cost Bomb (High)

**Attack Vectors:**
- Infinite loop triggers
- Recursive tool calls
- Intentional cost attacks
- Poorly designed skills

**Detection Opportunities at Proxy:**
- API call frequency anomalies
- Similar request patterns
- Budget consumption rate

**Risk Rating:** Medium likelihood × Medium impact = **High**

### 5. Tool Abuse (High)

**Attack Vectors:**
- Shell command injection
- Unauthorized file access
- Network reconnaissance
- Privilege escalation via tools

**Detection Opportunities at Proxy:**
- Dangerous command patterns
- Sensitive path access
- Suspicious network destinations
- Permission violations

**Risk Rating:** Low likelihood × High impact = **High**

### 6. Skill Supply Chain (Medium)

**Attack Vectors:**
- Malicious skill installation
- Skill behavior changes after update
- Time-bomb activation patterns
- Dependency compromise

**Detection Opportunities at Proxy:**
- Behavior drift from baseline
- Permission scope violations
- Unexpected network connections
- VirusTotal hash reputation

**Risk Rating:** Low likelihood × High impact = **Medium**

### 7. Behavioral Anomalies (Medium)

**Attack Vectors:**
- Compromised agent behavior
- Subtle goal deviation
- Cross-agent contamination
- Long-term data collection

**Detection Opportunities at Proxy:**
- Deviation from baseline metrics
- Unusual time-of-day activity
- Model/tool access pattern changes
- Conversation structure anomalies

**Risk Rating:** Low likelihood × Medium impact = **Medium**

## MITRE ATLAS Mapping

| ATLAS Technique | ClawShell Detection |
|-----------------|---------------------|
|AML.T0043 - Prompt Injection | Prompt Injection Detector |
|AML.T0044 - Social Engineering | Behavioral Anomaly |
|AML.T0047 - Side-Channel Attack | Data Exfil Detector |
|AML.T0051 - LLM Prompt Extraction | Prompt Injection Detector |
|AML.T0054 - Misdirection | Behavioral Anomaly |
|AML.T0055 - LLM Data Leakage | Data Exfil Detector |
|AML.T0056 - LLM Tool Use Manipulation | Tool Abuse Detector |

## Attack Scenarios

### Scenario 1: Prompt Injection via Document

```
1. Attacker uploads document with hidden instructions
2. Agent processes document, extracts "ignore previous instructions..."
3. Injection alters agent behavior
4. ClawShell detects injection pattern in request
5. Action: BLOCK request, ALERT user
```

### Scenario 2: Credential Exposure

```
1. User pastes error log with AWS keys
2. Agent conversation includes credentials
3. ClawShell detects credential pattern
4. Action: REDACT keys, ALERT user, LOG event
```

### Scenario 3: Runaway Loop

```
1. Skill triggers recursive tool calls
2. API call rate spikes (100+ calls/minute)
3. ClawShell detects frequency anomaly
4. Action: THROTTLE, ALERT, potential KILL if threshold exceeded
```

### Scenario 4: Data Exfiltration Attempt

```
1. Compromised skill encodes data in base64
2. Agent attempts to output encoded blob
3. ClawShell detects encoding pattern + high entropy
4. Action: BLOCK response, QUARANTINE, ALERT
```

### Scenario 5: Tool Abuse

```
1. Agent attempts `curl | bash` command
2. ClawShell detects dangerous shell pattern
3. Action: BLOCK request, ALERT, policy violation logged
```

## Detection Confidence Levels

| Level | Score | Action |
|-------|-------|--------|
| High | 0.8-1.0 | Immediate BLOCK/QUARANTINE |
| Medium | 0.5-0.79 | ALERT + WARN |
| Low | 0.2-0.49 | LOG only |
| Very Low | 0-0.19 | No action (noise) |

## Response Escalation Matrix

| Detection Type | First Offense | Second (24h) | Third (24h) |
|----------------|---------------|--------------|-------------|
| Prompt Injection | ALERT | BLOCK | QUARANTINE |
| Data Exfil | WARN | BLOCK | QUARANTINE |
| Credential | REDACT + ALERT | BLOCK | QUARANTINE |
| Runaway | THROTTLE | THROTTLE + ALERT | KILL |
| Tool Abuse | BLOCK | BLOCK + ALERT | KILL |
| Anomaly | LOG | ALERT | THROTTLE |

## False Positive Mitigation

1. **Feedback Loop**: Users can dismiss false positives
2. **Adaptive Thresholds**: Learn from dismissals
3. **Context Awareness**: Code blocks vs natural language
4. **Confidence Scoring**: Only act on high-confidence detections
5. **Severity-based Cooling**: Reduce alert frequency per category

## References

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATLAS Framework](https://atlas.mitre.org/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
