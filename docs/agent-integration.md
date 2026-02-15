# Agent Integration Guide

Complete guide for connecting AI agents to ClawShell.

## Quick Start

```
┌──────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Your Agent  │ ───▶ │  ACC Proxy       │ ───▶ │  LLM Provider   │
│  (OpenClaw)  │ ◀─── │  (Track & Route) │ ◀─── │  (Anthropic)    │
└──────────────┘      └──────────────────┘      └─────────────────┘
```

## Step 1: Create API Key

1. Go to **Dashboard → API Keys**
2. Click **Create Key**
3. Enter a name (e.g., "OpenClaw Production")
4. Copy the generated key (starts with `acc_`)

## Step 2: Configure Your Agent

Replace your LLM provider configuration with the ClawShell proxy.

---

## Integration Examples

### OpenClaw

```json
{
  "llm": {
    "provider": "anthropic",
    "baseUrl": "https://your-acc-proxy.vercel.app",
    "apiKey": "acc_YOUR_KEY_HERE",
    "model": "claude-sonnet-4-20250514"
  }
}
```

### Cursor IDE

Settings → Models → OpenAI Compatible:

```
Base URL: https://your-acc-proxy.vercel.app/v1
API Key: acc_YOUR_KEY_HERE
```

### Continue (VS Code)

`.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Claude via ACC",
      "provider": "anthropic",
      "apiBase": "https://your-acc-proxy.vercel.app",
      "apiKey": "acc_YOUR_KEY_HERE",
      "model": "claude-sonnet-4-20250514"
    }
  ]
}
```

### Aider

```bash
export ANTHROPIC_BASE_URL=https://your-acc-proxy.vercel.app
export ANTHROPIC_API_KEY=acc_YOUR_KEY_HERE
aider --model claude-sonnet-4-20250514
```

### LangChain (Python)

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    anthropic_api_url="https://your-acc-proxy.vercel.app",
    anthropic_api_key="acc_YOUR_KEY_HERE"
)
```

### OpenAI SDK (Python)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-acc-proxy.vercel.app/v1",
    api_key="acc_YOUR_KEY_HERE"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Anthropic SDK (Python)

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="https://your-acc-proxy.vercel.app",
    api_key="acc_YOUR_KEY_HERE"
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### HTTP Request (curl)

```bash
curl https://your-acc-proxy.vercel.app/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: acc_YOUR_KEY_HERE" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Request Headers

| Header | Description |
|--------|-------------|
| `x-acc-api-key` | Your API key (required) |
| `x-acc-agent-id` | Agent identifier for tracking |
| `x-acc-workflow` | Workflow name for categorization |

## Response Headers

| Header | Description |
|--------|-------------|
| `x-acc-cost` | Cost in USD for this request |
| `x-acc-tokens` | Total tokens used |
| `x-acc-model` | Model used (may differ if downgraded) |

---

## Supported Providers

| Provider | Endpoint | Models |
|----------|----------|--------|
| Anthropic | `/v1/messages` | claude-sonnet-4, claude-opus-4, claude-haiku-4 |
| OpenAI | `/v1/chat/completions` | gpt-4o, gpt-4o-mini, o1, o3-mini |
| Google | `/v1/messages` | gemini-2.5-pro, gemini-2.5-flash |

---

## Testing

### Health Check

```bash
curl https://your-acc-proxy.vercel.app/health
```

### Test Request

```bash
curl https://your-acc-proxy.vercel.app/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: acc_YOUR_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model": "claude-haiku-4", "max_tokens": 100, "messages": [{"role": "user", "content": "Hi"}]}' \
  -i
```

Check response headers for `x-acc-cost` and `x-acc-tokens`.

---

## Task Tracking Workflow

ClawShell provides a comprehensive task tracking system that allows agents to report their work in real-time.

### Overview

```
┌─────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│   Your Agent    │────▶│  Task API         │────▶│  Dashboard       │
│                 │     │  /api/agents/*    │     │  /agents         │
└─────────────────┘     └───────────────────┘     └──────────────────┘
        │                       │                          │
        │   1. Register         │                          │
        │──────────────────────▶│                          │
        │                       │                          │
        │   2. Start Task       │                          │
        │──────────────────────▶│                          │
        │                       │                          │
        │   3. Update Progress  │   Real-time Updates      │
        │──────────────────────▶│─────────────────────────▶│
        │                       │                          │
        │   4. Complete/Fail    │                          │
        │──────────────────────▶│─────────────────────────▶│
```

### Using the Agent Tracker Library

```typescript
import { AgentTracker, trackOperation } from '@/lib/agent-tracker'

// Create tracker instance
const tracker = new AgentTracker({
  name: 'My Coding Agent',
  agent_type: 'custom',
  default_model: 'claude-sonnet-4-5-20250915',
  default_provider: 'anthropic',
  baseUrl: 'https://your-acc-instance.vercel.app'
})

// Register the agent
await tracker.register()

// Start tracking a task
const task = await tracker.startTask({
  task_id: 'implement-auth-001',
  title: 'Implement user authentication',
  task_type: 'coding',
  description: 'Add OAuth2 login flow'
})

// Update progress
await task.updateProgress(25)
await task.updateProgress(50)

// Add token usage (increments)
await task.addTokens(1000, 500, 0.002)

// Complete the task
await task.complete({
  result_summary: 'Authentication implemented successfully'
})

// Or mark as failed
await task.fail('API rate limit exceeded')
```

### Quick Operation Tracking

For simple operations, use the `trackOperation` helper:

```typescript
import { createAgentTracker, trackOperation } from '@/lib/agent-tracker'

const tracker = createAgentTracker({ name: 'Quick Agent' })
await tracker.register()

const result = await trackOperation(
  tracker,
  { task_id: 'quick-task', title: 'Process data', task_type: 'analysis' },
  async (task) => {
    // Your operation here
    await task.updateProgress(50)
    const data = await processData()

    // Add token usage as you go
    await task.addTokens(500, 200, 0.001)

    return data
  }
)
// Task is automatically completed or failed based on the operation result
```

### API Endpoints

#### Register Agent

```http
POST /api/agents/register
Content-Type: application/json

{
  "name": "My Agent",
  "description": "A coding assistant",
  "agent_type": "custom",
  "default_model": "claude-sonnet-4-5-20250915",
  "tags": ["coding", "research"]
}
```

Response:
```json
{
  "success": true,
  "agent": {
    "id": "uuid-here",
    "name": "My Agent",
    "status": "active"
  }
}
```

#### Create Task

```http
POST /api/agents/tasks
Content-Type: application/json

{
  "agent_id": "agent-uuid",
  "task_id": "unique-task-id",
  "title": "Task title",
  "task_type": "coding",
  "model": "claude-sonnet-4-5-20250915"
}
```

#### Update Task

```http
PATCH /api/agents/tasks
Content-Type: application/json

{
  "agent_id": "agent-uuid",
  "task_id": "unique-task-id",
  "status": "running",
  "progress_percent": 50,
  "input_tokens": 1000,
  "output_tokens": 500,
  "cost_usd": 0.002
}
```

#### Get Active Tasks

```http
GET /api/agents/tasks?active_only=true
```

### Task Status Lifecycle

```
  pending ──▶ running ──▶ completed
      │           │
      │           ├──▶ paused ──▶ running
      │           │
      │           └──▶ failed
      │
      └──▶ cancelled
```

### Dashboard Features

- **Overview Tab**: See all agents and their active tasks
- **Tasks Tab**: View all task history with filtering
- **Live Updates**: Auto-refresh every 3-5 seconds
- **Agent Details**: Click an agent to see detailed metrics

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Onboarding Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CREATE API KEY                                              │
│     Dashboard → API Keys → Create Key → acc_xxxxx               │
│                                                                 │
│  2. REGISTER AGENT                                              │
│     POST /api/agents/register with agent details                │
│                                                                 │
│  3. CONFIGURE PROXY (Optional)                                  │
│     Agent Config → Set baseUrl → Set apiKey                     │
│                                                                 │
│  4. TRACK TASKS                                                 │
│     Use AgentTracker library to report task progress            │
│                                                                 │
│  5. SET BUDGET (Optional)                                       │
│     Dashboard → Budgets → Create Budget for Agent               │
│                                                                 │
│  6. MONITOR                                                     │
│     Dashboard → Agents → Real-time task tracking                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
