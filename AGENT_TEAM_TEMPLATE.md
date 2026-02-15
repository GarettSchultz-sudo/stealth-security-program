# Agent Team Execution Guide Template

> **How to use this template:**
> 1. Fill in the **Input Criteria** section below. Each field accepts EITHER a concrete value OR a research request.
> 2. Research requests get resolved during Phase 1 (Assessment) by research teammates and stored in Memory as decisions.
> 3. Later phases reference those Memory decisions with `{{RESOLVED:field_name}}` instead of hardcoded values.
> 4. Copy the **Phase N** block once per major feature. Delete optional sections you don't need.
> 5. Choose a **Team Topology**: `solo` (single agent, no teams), `squad` (one persistent team, phased tasks), or `swarm` (per-wave teams with full parallelism).
> 6. If using squad/swarm topology, define **waves** in `team_config` grouping independent phases for parallel execution.

---

## Core Concept: Teams as the Execution Primitive

Unlike loop-based execution where a single agent iterates until a completion signal is detected,
the Agent Team model treats **teams, tasks, and messages** as first-class execution primitives:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXECUTION MODEL COMPARISON                       │
├──────────────────────────────────┬──────────────────────────────────────┤
│  Loop-Based (ralph-loop)         │  Team-Based (agent teams)            │
├──────────────────────────────────┼──────────────────────────────────────┤
│  Single agent iterates           │  Multiple agents work concurrently   │
│  <promise> tags signal done      │  TaskUpdate(status=completed) done   │
│  Loop counter limits iterations  │  Task dependencies limit ordering    │
│  Progress via file reads         │  Progress via TaskList + SendMessage │
│  Teams bolted on optionally      │  Teams ARE the execution model       │
│  One context window, one thread  │  N context windows, N threads        │
│  /ralph-loop:ralph-loop "..."    │  TeamCreate → TaskCreate → Task(...)│
│  /ralph-loop:cancel-ralph        │  SendMessage(shutdown_request)       │
└──────────────────────────────────┴──────────────────────────────────────┘
```

### The Four Primitives

| Primitive | Tool | Purpose |
|-----------|------|---------|
| **Team** | `TeamCreate` / `TeamDelete` | Scoped workspace with shared task list. One team per wave (swarm) or one persistent team (squad). |
| **Task** | `TaskCreate` / `TaskUpdate` / `TaskList` | Unit of work with status, owner, dependencies. Replaces promises — a phase is "done" when its task is `completed`. |
| **Message** | `SendMessage` | Real-time coordination between agents. Teammates push status to lead instead of polling files. |
| **Planning Files** | `task_plan.md` / `findings.md` / `progress.md` | Persistent ground truth that survives context window resets, session boundaries, and teammate turnover. Every phase reads AND writes these files. Created via `/planning-with-files:plan`. |

### Planning Files: The Persistent State Layer

Teams, tasks, and messages are ephemeral — they exist only while the team is running.
Planning files are the **durable state** that persists across sessions, context resets, and team lifecycles.

```
┌─────────────────────────────────────────────────────────────────────┐
│  EPHEMERAL (lives during team execution)                             │
│                                                                      │
│  TeamCreate / TaskCreate / SendMessage / TaskList / TeamDelete       │
│  └── Gone when team is deleted or session ends                       │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  DURABLE (persists forever in the repo)                              │
│                                                                      │
│  task_plan.md ── Phase breakdown, status, key questions, errors      │
│  findings.md  ── Research results, gap analysis, security findings   │
│  progress.md  ── Action log, test results, checkpoint records        │
│  Memory MCP   ── Decision_ entities, cross-session state             │
│                                                                      │
│  └── Survives: context resets, session ends, teammate shutdowns,     │
│       team deletion, even new conversation windows                   │
└─────────────────────────────────────────────────────────────────────┘
```

Every teammate MUST:
1. **Read** task_plan.md + findings.md + progress.md at the START of their work
2. **Write** findings to findings.md as they discover things (every 2-3 actions)
3. **Update** progress.md with actions taken, commands run, test results
4. **Update** task_plan.md phase status (pending → in_progress → complete)
5. **Sync** Memory MCP entities for cross-teammate decision sharing

### Control Flow

```
TeamCreate ──→ TaskCreate (with dependencies) ──→ Task (spawn teammates)
                                                        │
                    ┌───────────────────────────────────┘
                    │
                    ▼
            Teammates work autonomously:
            ├── Read task_plan.md / findings.md / progress.md (ground truth)
            ├── Read Memory for resolved decisions
            ├── Implement their assigned phase
            ├── Write findings.md + progress.md as they work
            ├── TaskUpdate(status="completed") when done
            └── SendMessage to lead with results summary
                    │
                    ▼
            Lead monitors via TaskList + incoming messages
            Lead cross-checks progress.md for detailed state
                    │
                    ▼
            All tasks completed? ──→ SendMessage(shutdown_request) ──→ TeamDelete
                                         │
                                         ▼
                                  Planning files persist ──→ Next wave / Done
```

---

## Input Criteria

Every field below accepts one of three input modes:

| Mode | Syntax | When to use |
|------|--------|-------------|
| **Concrete** | `value: "FastAPI"` | You already know the answer |
| **Research** | `research: "What backend framework best handles..."` | You want Phase 1 research teammates to decide |
| **Constrained research** | `research: "Compare X vs Y for..."` | You've narrowed it but want validation |

Fields marked `(required)` must have at least a research request. Fields marked `(optional)` can be omitted entirely.

```yaml
# ╔══════════════════════════════════════════════════════════════╗
# ║  PROJECT IDENTITY (required)                                 ║
# ╚══════════════════════════════════════════════════════════════╝
project_name: "{{PROJECT_NAME}}"               # Always concrete
project_slug: "{{PROJECT_SLUG}}"               # Always concrete (lowercase, hyphens)
prompt_file: "{{PROMPT_FILE}}"                 # The prompt doc this guide executes
goal_summary: "{{GOAL_SUMMARY}}"               # 1-2 sentence goal. Always concrete.

# ╔══════════════════════════════════════════════════════════════╗
# ║  ARCHITECTURE (concrete OR research per field)               ║
# ╚══════════════════════════════════════════════════════════════╝
tech_stack:
  backend_framework:                           # Pick ONE mode per field:
    value: "FastAPI"                           #   Concrete: you know
    # -- OR --
    # research: "What Python backend framework is best for real-time microservices with WebSocket support?"
    # constraints: ["Must be Python", "Must support async"]  # optional narrowing

  backend_language:
    value: "Python"
    # research: "What language best balances developer velocity and production performance for a chat platform?"

  frontend_framework:
    value: "React"
    # research: "Compare React vs Vue vs Svelte for a real-time chat UI with complex state management"

  database:
    value: "PostgreSQL"
    # research: "What database handles mixed read-heavy chat history and write-heavy message ingestion?"
    # constraints: ["Must be self-hostable", "Must support full-text search"]

  cache:
    value: "Redis"
    # research: "Do we need a cache layer, and if so what fits best for pub/sub + session storage?"

  deployment:
    value: "Docker Compose"
    # research: "What deployment approach works best for self-hosted, single-server, 50-100 users?"
    # constraints: ["No Kubernetes", "Must be simple for non-DevOps users"]

  client_type:
    value: "Electron desktop"
    # research: "What client platform reaches the most users for a self-hosted chat app?"
    # constraints: ["Must support WebRTC", "Must work on Windows/Mac/Linux"]

# Service list: concrete if you have a codebase, research if greenfield
services:
  value:                                       # Concrete: list known services
    - "auth"
    - "user"
    - "server"
    - "channel"
    - "message"
    - "file"
    - "webrtc"
    - "websocket"
  # -- OR --
  # research: "What service boundaries make sense for a chat platform with text, voice, and file sharing?"
  # constraints: ["Minimize inter-service calls", "Each service owns its own DB tables"]

service_base_path: "backend/services"          # Where services live in the repo
service_entry_file: "main.py"                  # Main file per service

# ╔══════════════════════════════════════════════════════════════╗
# ║  DEPLOYMENT TARGET (required)                                ║
# ╚══════════════════════════════════════════════════════════════╝
hosting:
  value: "self-hosted"
  # research: "Should this be self-hosted, cloud-managed, or hybrid for a small team's internal chat?"

target_users:
  value: "50-100 concurrent"
  # research: "What user scale should we design for given a single-server Docker Compose deployment?"

geo_distribution:
  value: "US geo-distributed"
  # research: "What geographic distribution pattern matters for a US-based team chat with voice?"

# ╔══════════════════════════════════════════════════════════════╗
# ║  FEATURES (required - list what needs implementation)        ║
# ╚══════════════════════════════════════════════════════════════╝
# Each feature becomes a task assigned to a teammate.
# Use 'research' within a feature to investigate HOW to implement it.
features:
  - name: "Real-Time Messaging"
    category: "websocket"
    critical_path: false
    approach:
      value: "WebSocket gateway with Redis pub/sub"
      # research: "What real-time messaging pattern works best for horizontal scaling without Kubernetes?"

  - name: "Voice Communication"
    category: "webrtc"
    critical_path: true                        # The riskiest/hardest feature
    approach:
      # research: "Compare mediasoup vs LiveKit vs Janus for a self-hosted SFU supporting 20 concurrent voice users"
      constraints: ["Must work behind NAT", "Must be Docker-deployable", "Sub-200ms latency"]

  - name: "File Uploads"
    category: "storage"
    critical_path: false
    approach:
      value: "MinIO (S3-compatible) with presigned URLs"

# ╔══════════════════════════════════════════════════════════════╗
# ║  TEAM TOPOLOGY (required)                                    ║
# ╚══════════════════════════════════════════════════════════════╝
# Choose how phases map to teams and teammates:
#   "solo"   - No teams. Lead executes all phases directly via Task tool (lowest token cost)
#   "squad"  - One persistent team. Phases become tasks. Lead assigns tasks to teammates in order.
#   "swarm"  - Per-wave teams. Full parallelism. Teams created/destroyed per wave (highest throughput)

team_topology: "squad"                          # "solo" | "squad" | "swarm"

# Team configuration (only used when team_topology is "squad" or "swarm")
team_config:
  team_name: "{{PROJECT_SLUG}}-build"            # Team identifier
  delegate_lead: true                            # true = lead only coordinates, never implements
  require_plan_approval: true                    # Teammates must get plan approved before coding
  default_teammate_model: "sonnet"               # "sonnet" | "opus" | "haiku" per teammate

  # Waves: groups of phases that run in parallel.
  # Phases within a wave have NO dependencies on each other.
  # Waves run sequentially (wave 0 finishes before wave 1 starts).
  waves:
    - wave: 0
      mode: "lead-solo"                          # Lead runs these directly (no teammates)
      phases: ["step0", "phase1"]
    - wave: 1
      mode: "lead-solo"
      phases: ["phase2"]
    - wave: 2
      mode: "parallel"                           # Spawn teammates for these
      phases: ["phase3", "phase4", "phase5"]     # Must match feature names
      teammates:
        - name: "{{FEATURE_1_SLUG}}-dev"
          phase: "phase3"
          subagent_type: "general-purpose"        # or specialized type from Agent Selection Guide
        - name: "{{FEATURE_2_SLUG}}-dev"
          phase: "phase4"
          subagent_type: "general-purpose"
        - name: "{{FEATURE_3_SLUG}}-dev"
          phase: "phase5"
          subagent_type: "general-purpose"
    - wave: 3
      mode: "lead-solo"
      phases: ["phaseY"]
    - wave: 4
      mode: "parallel"
      phases: ["phaseD", "phaseF-prep"]          # Deployment + test prep can overlap
      teammates:
        - name: "deploy-engineer"
          phase: "phaseD"
          subagent_type: "general-purpose"
        - name: "test-engineer"
          phase: "phaseF-prep"
          subagent_type: "general-purpose"
    - wave: 5
      mode: "lead-solo"
      phases: ["phaseF"]                         # Final validation is always lead-solo

  # Quality gate: lead reviews each task before accepting completion
  quality_gates:
    require_tests_pass: true                     # Teammate must confirm tests pass
    require_code_review: true                    # Lead or peer reviews before task closes
    require_memory_checkpoint: true              # Teammate must save state to Memory MCP

# ╔══════════════════════════════════════════════════════════════╗
# ║  SUCCESS CRITERIA (required)                                 ║
# ╚══════════════════════════════════════════════════════════════╝
# Concrete items that the final phase validates. These should be specific and testable.
# Use 'research' if you need help defining what "good" looks like.
success_criteria:
  functional:
    - value: "50+ concurrent users connect from different locations"
    - value: "Text messaging with real-time delivery"
    - value: "Voice channels with clear audio across NAT"
    # - research: "What functional acceptance criteria are standard for production chat platforms?"

  infrastructure:
    - value: "SSL/TLS on all services"
    - value: "Database backups automated"
    # - research: "What infrastructure criteria matter for a self-hosted deployment?"

  deployment:
    - value: "Single command starts everything"
    - value: ".env.example documented"

  performance:
    - value: "Voice latency < 200ms coast-to-coast"
    - value: "Message delivery < 500ms"
    # - research: "What performance benchmarks are reasonable for 50-100 user self-hosted chat?"
```

---

## How Research Requests Flow Through the Template

```
Input Criteria                    Phase 1 Research Team             Phases 2+
┌─────────────────┐              ┌──────────────────┐            ┌──────────────────┐
│ backend_framework│              │  Research         │            │                  │
│   research: "X?" │─────────────│  teammates run    │            │ Read Memory:     │
│   constraints:   │   becomes   │  parallel searches│  stores    │ "Decision_       │
│   ["Must be Y"]  │   a task    │  (Octagon/PAL/    │──────────│  backend_fw"     │
│                  │   for the   │   Brave). Results │  Memory   │ → Use resolved   │
│                  │   research  │  sent via         │  entity   │   value          │
│                  │   team      │  SendMessage      │           │                  │
└─────────────────┘              └──────────────────┘            └──────────────────┘

┌─────────────────┐              ┌──────────────────┐            ┌──────────────────┐
│ backend_framework│              │                  │            │                  │
│   value: "FastAPI"│─────────────│  Skips research, │            │ Uses "FastAPI"   │
│                  │   passes    │  validates only   │  stores   │ directly         │
│                  │   through   │                  │──────────│                  │
└─────────────────┘              └──────────────────┘            └──────────────────┘
```

---

## Agent Team Architecture

### The Three Topologies

```
SOLO (team_topology: "solo")
════════════════════════════
No teams created. Lead executes each phase
by spawning one-off Task agents sequentially.
Cheapest. Simplest. For small or tightly coupled projects.

  Lead ──→ Task(phase1) ──→ Task(phase2) ──→ Task(phase3) ──→ ...

─────────────────────────────────────────────────────────────────

SQUAD (team_topology: "squad")
══════════════════════════════
One persistent team for the entire project.
Lead creates all tasks upfront with dependencies.
Spawns teammates as tasks become unblocked.
Team persists across all waves.

  TeamCreate("my-project-build")
       │
       ├── TaskCreate(phase1, no deps)
       ├── TaskCreate(phase2, blockedBy: phase1)
       ├── TaskCreate(phase3, blockedBy: phase2)   ─┐
       ├── TaskCreate(phase4, blockedBy: phase2)   ─┤ parallel
       ├── TaskCreate(phase5, blockedBy: phase2)   ─┘
       ├── TaskCreate(phaseD, blockedBy: 3,4,5)
       └── TaskCreate(phaseF, blockedBy: phaseD)
       │
       ├── Lead runs phase1 directly
       ├── Lead runs phase2 directly
       ├── Task(teammate for phase3) ║ Task(teammate for phase4) ║ Task(teammate for phase5)
       ├── Task(teammate for phaseD)
       └── Task(teammate for phaseF)
       │
  TeamDelete("my-project-build")

─────────────────────────────────────────────────────────────────

SWARM (team_topology: "swarm")
══════════════════════════════
Per-wave teams. Maximum isolation.
Each wave gets its own team, task list, and teammates.
Teams are created and destroyed per wave.
Highest throughput but highest token cost.

  Wave 0: TeamCreate("proj-wave-0") → solo phases → TeamDelete
  Wave 1: TeamCreate("proj-wave-1") → solo phases → TeamDelete
  Wave 2: TeamCreate("proj-wave-2") → 3 teammates → TeamDelete
  Wave 3: TeamCreate("proj-wave-3") → solo phases → TeamDelete
  Wave 4: TeamCreate("proj-wave-4") → 2 teammates → TeamDelete
  Wave 5: TeamCreate("proj-wave-5") → solo phases → TeamDelete
```

### Teammate Lifecycle (Squad and Swarm)

```
                    ┌─────────────────────────────────────────────────┐
                    │               TEAM LEAD (you)                   │
                    │  • Creates team via TeamCreate                   │
                    │  • Creates tasks via TaskCreate                  │
                    │  • Sets dependencies via TaskUpdate(addBlockedBy)│
                    │  • Spawns teammates via Task tool                │
                    │  • Monitors via TaskList + incoming messages     │
                    │  • Reviews work before accepting task completion │
                    │  • Sends shutdown_request when wave/project done │
                    └────────────┬────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
    │  Teammate A   │   │  Teammate B   │   │  Teammate C   │
    │  Phase 3 task │   │  Phase 4 task │   │  Phase 5 task │
    │               │   │               │   │               │
    │  1. TaskList  │   │  1. TaskList  │   │  1. TaskList  │
    │  2. TaskGet   │   │  2. TaskGet   │   │  2. TaskGet   │
    │  3. Claim task│   │  3. Claim task│   │  3. Claim task│
    │  4. Work      │   │  4. Work      │   │  4. Work      │
    │  5. TaskUpdate│   │  5. TaskUpdate│   │  5. TaskUpdate│
    │     completed │   │     completed │   │     completed │
    │  6. SendMsg   │   │  6. SendMsg   │   │  6. SendMsg   │
    │     to lead   │   │     to lead   │   │     to lead   │
    └───────────────┘   └───────────────┘   └───────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │        Shared Task List          │
                    │  ~/.claude/tasks/{team-name}/    │
                    │                                  │
                    │  Task 1: Phase 3 [completed]     │
                    │  Task 2: Phase 4 [in_progress]   │
                    │  Task 3: Phase 5 [completed]     │
                    │    (dependencies auto-resolved)  │
                    └─────────────────────────────────┘
```

### Wave Execution: Solo vs Squad vs Swarm

```
SOLO                                   SQUAD                                  SWARM
═════                                  ═════                                  ═════
Task(phase1)                           TeamCreate("proj-build")               TeamCreate("proj-w0")
  └→ wait                              TaskCreate(phase1..phaseF)             TaskCreate(step0, phase1)
Task(phase2)                           │                                      Lead runs solo → TeamDelete
  └→ wait                              ├─ Lead: phase1 directly               TeamCreate("proj-w1")
Task(phase3)                           ├─ Lead: phase2 directly               TaskCreate(phase2)
  └→ wait                              ├─ Task(A, team) ║ Task(B) ║ Task(C)   Lead runs solo → TeamDelete
Task(phase4)                           │  (phases 3,4,5 unblocked by phase2) TeamCreate("proj-w2")
  └→ wait                              ├─ Task(D, team)                       3x TaskCreate + 3x Task(...)
Task(phase5)                           ├─ Task(F, team)                         → 3 teammates → TeamDelete
  └→ wait                              └─ TeamDelete                          TeamCreate("proj-w3") ...
Task(phaseD) ...                                                              ...
```

---

## How Completion Works (Tasks Replace Promises)

In loop-based execution, a phase is "done" when the agent emits a `<promise>` tag and the loop detects it.
In team-based execution, a phase is "done" when:

```
1. Teammate calls: TaskUpdate(taskId="...", status="completed")
   └─ This is the AUTHORITATIVE completion signal

2. Teammate sends: SendMessage(
     type="message",
     recipient="team-lead",
     content="Phase 3 complete. All WebSocket handlers implemented, tests passing.",
     summary="Phase 3 done"
   )
   └─ This gives the lead CONTEXT about what was accomplished

3. Lead verifies via: TaskList()
   └─ Checks all tasks in the wave show status: "completed"

4. Lead optionally reviews:
   └─ Read progress.md, Memory entities, run tests
   └─ If unsatisfied: TaskUpdate(status="in_progress") to reopen + SendMessage with feedback

5. Wave is done when: ALL tasks in the wave are "completed" AND lead is satisfied
```

### Completion vs Promises: Quick Comparison

| Loop-Based (Promise) | Team-Based (Task Status) |
|---|---|
| `<promise>BOOTSTRAP_COMPLETE</promise>` | `TaskUpdate(taskId="1", status="completed")` |
| Loop detects tag and stops | Lead sees status change via TaskList |
| Single agent, single signal | Teammate signals + lead verifies |
| Max iterations as safety net | Lead can reopen tasks if unsatisfied |
| `/ralph-loop:cancel-ralph` to abort | `SendMessage(type="shutdown_request")` |

---

# Agent Team Execution Guide for {{PROMPT_FILE}}

**Purpose**: {{GOAL_SUMMARY}}

**Execution Order**: Step 0 -> Phase 1{{PHASE_ARROW_CHAIN}}

**State Continuity**: Each phase reads accumulated state from `task_plan.md`, `findings.md`, `progress.md`, and Memory MCP entities written by prior phases/teammates.

**Team Topology**: {{TEAM_TOPOLOGY}} {{IF_TEAM_MODE}}({{PARALLEL_WAVE_COUNT}} parallel waves, max {{MAX_CONCURRENT}} concurrent teammates){{/IF_TEAM_MODE}}

**Control Flow**: {{IF_SOLO}}Lead spawns one-off Task agents for each phase sequentially. No teams, no task lists, no message passing.{{/IF_SOLO}}{{IF_SQUAD}}One persistent team. All tasks created upfront with dependencies. Teammates spawned as tasks become unblocked. Team persists across the entire build.{{/IF_SQUAD}}{{IF_SWARM}}Per-wave teams with full isolation. Teams created and destroyed per wave. Maximum parallelism.{{/IF_SWARM}}

**Open Research**: {{COUNT}} fields require research resolution in Phase 1 before implementation can begin.

---

## Step 0: Bootstrap

**Purpose**: Initialize all tools, register project, load prior context, set up planning files.
**Depends on**: Nothing (this is first)
**Produces**: Serena onboarded, Memory initialized, planning files created, team config stored
**Assigned to**: Lead (always)

### Solo Topology

```
Task(
  subagent_type="general-purpose",
  description="Bootstrap project",
  prompt="Execute {{PROMPT_FILE}} Step 0: Bootstrap.

TASKS:
1. mcp__serena__check_onboarding_performed() - check if project is registered
2. mcp__serena__onboarding() - register project if not already done
3. mcp__serena__initial_instructions() - read Serena operating manual
4. mcp__memory__read_graph() - check for any prior context from previous sessions
5. mcp__memory__search_nodes('{{PROJECT_SLUG}}') - find related prior work
6. /planning-with-files:plan '{{PROJECT_NAME}} - {{GOAL_SUMMARY}}'
7. Verify task_plan.md, findings.md, progress.md are created
8. mcp__memory__create_entities([{name: 'Project_{{PROJECT_SLUG}}_Start', entityType: 'milestone', observations: ['{{GOAL_SUMMARY}}', 'Target: {{HOSTING}}, {{TARGET_USERS}}, {{GEO_DISTRIBUTION}}', 'Open research questions: {{RESEARCH_FIELD_LIST}}', 'Team topology: {{TEAM_TOPOLOGY}}']}])
9. /checkpoint:create 'pre-assessment-bootstrap'

DONE WHEN: Serena onboarded, Memory initialized, planning files exist, checkpoint saved."
)
```

### Squad / Swarm Topology

The lead runs Step 0 directly (before any team exists), then creates the team:

```
# 1. Lead runs bootstrap tasks directly (same as solo above)

# 2. Create the team (squad: one team for entire project; swarm: first wave team)
TeamCreate(
  team_name="{{PROJECT_SLUG}}-build",   # squad
  # team_name="{{PROJECT_SLUG}}-wave-0", # swarm
  description="{{PROJECT_NAME}}: {{GOAL_SUMMARY}}"
)

# 3. Store team config in Memory for teammates to discover
mcp__memory__create_entities([{
  name: 'TeamConfig_{{PROJECT_SLUG}}',
  entityType: 'team_config',
  observations: [
    'team_name: {{TEAM_NAME}}',
    'topology: {{TEAM_TOPOLOGY}}',
    'waves: {{WAVE_DEFINITIONS}}',
    'delegate_lead: {{DELEGATE_LEAD}}',
    'require_plan_approval: {{REQUIRE_PLAN_APPROVAL}}'
  ]
}])

# 4. Create Phase 1 task (squad: part of full task graph; swarm: only task in wave-0)
TaskCreate(
  subject="Phase 1: Assessment + Technology Selection",
  description="Full gap analysis + resolve all {{COUNT}} open research questions into Memory Decision_ entities.",
  activeForm="Running assessment and technology selection"
)
```

---

## Phase 1: Assessment + Technology Selection

**Purpose**: Full gap analysis of the codebase AND resolution of all open research questions into concrete technology decisions.
**Depends on**: Step 0 (Serena onboarded, planning files exist)
**Produces**: Populated `findings.md`, detailed `task_plan.md`, Memory entities with assessment results AND all technology decisions resolved
**Assigned to**: Lead (solo/squad) or research teammates (swarm with competing hypotheses)

> **Key behavior:** This phase has a dedicated "RESOLVE OPEN QUESTIONS" section that turns every `research:`
> field from Input Criteria into a concrete Memory decision entity. Later phases read these decisions
> from Memory instead of using hardcoded values.

### Solo / Squad: Lead Runs Directly

```
Task(
  subagent_type="general-purpose",
  description="Assessment and tech selection",
  prompt="Execute {{PROMPT_FILE}} Phase 1: Assessment + Technology Selection.

Read task_plan.md and progress.md for current state.

PART A: RESOLVE OPEN RESEARCH QUESTIONS
========================================
The following fields need research-based decisions. For each one:
  (a) Run parallel research using Octagon + Brave + PAL
  (b) Synthesize into a recommendation with rationale
  (c) AskUserQuestion to confirm or override the recommendation
  (d) Store as Memory entity: Decision_<field_name>

{{BLOCK:RESEARCH_FIELD}}
OPEN QUESTION: {{FIELD_NAME}}
  Request: '{{RESEARCH_REQUEST}}'
  Constraints: {{CONSTRAINTS}}
  Research actions:
  - mcp__octagon-deep-research-mcp__octagon-deep-research-agent: '{{RESEARCH_REQUEST}} Consider: {{CONSTRAINTS}}. Evaluate in context of {{GOAL_SUMMARY}}. Year: 2026.'
  - mcp__brave-search__brave_web_search: '{{BRAVE_SEARCH_VARIANT}} 2026'
  - mcp__pal__thinkdeep: 'For a project that {{GOAL_SUMMARY}}, evaluate: {{RESEARCH_REQUEST}}'
  After synthesis:
  - AskUserQuestion: 'Based on research, I recommend {{RECOMMENDATION}} because {{RATIONALE}}. Options: [recommended] / [alternative_1] / [alternative_2] / [custom]'
  - mcp__memory__create_entities([{name: 'Decision_{{FIELD_NAME}}', entityType: 'technology_decision', observations: ['Question: {{RESEARCH_REQUEST}}', 'Decision: <chosen_value>', 'Rationale: <why>', 'Alternatives considered: <list>', 'Constraints applied: {{CONSTRAINTS}}']}])
{{/BLOCK:RESEARCH_FIELD}}

PART B: CODEBASE GAP ANALYSIS
==============================
1. GAP ANALYSIS (Serena):
   - mcp__serena__search_for_pattern('TODO|FIXME|mock|stub|placeholder|NotImplemented') across all {{SERVICE_BASE_PATH}}/
   - mcp__serena__list_dir('{{SERVICE_BASE_PATH}}', recursive=True)
   - mcp__serena__get_symbols_overview() on every {{SERVICE_ENTRY_FILE}} in {{SERVICE_BASE_PATH}}/*/
   - Document every gap found in findings.md

2. ARCHITECTURE EVALUATION (PAL):
   - mcp__pal__thinkdeep: 'Evaluate the {{PROJECT_NAME}} architecture using the resolved technology decisions from Memory. Target: {{HOSTING}}, {{TARGET_USERS}}, {{GEO_DISTRIBUTION}}.'
   - mcp__pal__challenge: '{{ARCHITECTURE_CHALLENGE_QUESTION}}'
   - Store results in Memory

3. SECURITY AUDIT (Agent):
   - Task(subagent_type='comprehensive-review:security-auditor') on {{SERVICE_BASE_PATH}}/
   - mcp__pal__codereview focusing on security vulnerabilities
   - Document findings in findings.md

4. DATABASE ANALYSIS (Agent):
   - Task(subagent_type='database-cloud-optimization:database-optimizer') on database schemas

PART C: SYNTHESIZE
===================
- Verify ALL research questions from Part A have Decision_ entities in Memory
- Compile gap analysis + architecture evaluation + security findings into findings.md
- Create task_plan.md with per-phase breakdown referencing resolved decisions
- mcp__pal__consensus on overall architecture approach using resolved tech stack
- Update progress.md with Phase 1 completion and all decisions made
- /checkpoint:create 'phase1-assessment-complete'

{{IF_SQUAD_OR_SWARM}}
- TaskUpdate(taskId='...', status='completed')
- SendMessage(type='message', recipient='team-lead', content='Phase 1 complete. All {{COUNT}} research questions resolved. Findings documented.', summary='Phase 1 assessment done')
{{/IF_SQUAD_OR_SWARM}}

DONE WHEN:
  1. ALL research fields have Decision_ entities in Memory
  2. findings.md has comprehensive gap analysis
  3. task_plan.md has detailed phase breakdown using resolved technology choices
  4. User has confirmed or overridden every technology recommendation"
)
```

### Swarm: Competing Hypotheses for Research-Heavy Phase 1

When there are 8+ open research questions, spawn parallel research teammates:

```
TeamCreate(team_name="{{PROJECT_SLUG}}-research", description="Phase 1 parallel research")

# Create research tasks — one per domain
TaskCreate(
  subject="Research: Backend & Infrastructure decisions",
  description="Resolve: backend_framework, backend_language, cache, deployment. Store Decision_ entities in Memory.",
  activeForm="Researching backend stack"
)
TaskCreate(
  subject="Research: Frontend & Client decisions",
  description="Resolve: frontend_framework, client_type. Store Decision_ entities in Memory.",
  activeForm="Researching frontend stack"
)
TaskCreate(
  subject="Research: Data & Services decisions",
  description="Resolve: database, services, feature approaches. Store Decision_ entities in Memory.",
  activeForm="Researching data architecture"
)
TaskCreate(
  subject="Codebase Gap Analysis",
  description="Full Serena-based gap analysis, security audit, DB analysis. Write findings.md.",
  activeForm="Analyzing codebase gaps"
)

# Spawn teammates in parallel
Task(
  subagent_type="Explore",
  team_name="{{PROJECT_SLUG}}-research",
  name="backend-researcher",
  model="sonnet",
  prompt="You are backend-researcher on the {{PROJECT_SLUG}}-research team.
  YOUR TASK: Research and resolve backend technology decisions.
  ..."
)
Task(
  subagent_type="Explore",
  team_name="{{PROJECT_SLUG}}-research",
  name="frontend-researcher",
  model="sonnet",
  prompt="You are frontend-researcher on the {{PROJECT_SLUG}}-research team.
  YOUR TASK: Research and resolve frontend technology decisions.
  ..."
)
# ... more teammates ...

# After all complete: lead synthesizes, asks user to confirm, creates final Decision_ entities
# Then: shutdown all researchers, TeamDelete
```

---

## Team Lead Orchestration (Squad / Swarm)

> **Skip this section if `team_topology` is `"solo"`.** In solo mode, run each phase
> as a direct `Task(...)` call in order. In squad/swarm mode, the lead orchestrates
> teammates through the task list and messaging.
>
> **When to use:** After Phase 1 completes and all research questions are resolved. The lead
> uses this pattern to execute all remaining phases.

### Squad Orchestration Pattern

In squad mode, the team persists and all tasks exist upfront:

```
# ═══════════════════════════════════════════════════════════════
# SETUP (run once after Phase 1 completes)
# ═══════════════════════════════════════════════════════════════

# Team already exists from Step 0. Create all remaining tasks with dependencies.

TaskCreate(
  subject="Phase 2: {{PHASE_2_TITLE}}",
  description="{{PHASE_2_PURPOSE}}",
  activeForm="Building {{PHASE_2_TITLE}}"
)
# Phase 2 has no blockedBy (Phase 1 already done)

TaskCreate(
  subject="Phase 3: {{FEATURE_1_NAME}}",
  description="{{FEATURE_1_PURPOSE}}",
  activeForm="Implementing {{FEATURE_1_NAME}}"
)
TaskUpdate(taskId="phase3_id", addBlockedBy=["phase2_id"])

TaskCreate(
  subject="Phase 4: {{FEATURE_2_NAME}}",
  description="{{FEATURE_2_PURPOSE}}",
  activeForm="Implementing {{FEATURE_2_NAME}}"
)
TaskUpdate(taskId="phase4_id", addBlockedBy=["phase2_id"])

TaskCreate(
  subject="Phase 5: {{FEATURE_3_NAME}}",
  description="{{FEATURE_3_PURPOSE}}",
  activeForm="Implementing {{FEATURE_3_NAME}}"
)
TaskUpdate(taskId="phase5_id", addBlockedBy=["phase2_id"])

{{IF_CLIENT_INTEGRATION}}
TaskCreate(
  subject="Phase Y: Client Integration",
  description="Connect client to real backend APIs, replace all mock data",
  activeForm="Integrating client"
)
TaskUpdate(taskId="phaseY_id", addBlockedBy=["phase3_id", "phase4_id", "phase5_id"])
{{/IF_CLIENT_INTEGRATION}}

TaskCreate(
  subject="Phase D: Deployment & Hardening",
  description="Production deployment, SSL, secrets, monitoring",
  activeForm="Hardening deployment"
)
TaskUpdate(taskId="phaseD_id", addBlockedBy=[{{IF_CLIENT_INTEGRATION}}"phaseY_id"{{/IF_CLIENT_INTEGRATION}}{{IF_NO_CLIENT}}"phase3_id", "phase4_id", "phase5_id"{{/IF_NO_CLIENT}}])

TaskCreate(
  subject="Phase F: Testing & Validation",
  description="Comprehensive testing, load tests, security audit, success criteria verification",
  activeForm="Final validation"
)
TaskUpdate(taskId="phaseF_id", addBlockedBy=["phaseD_id"])

# ═══════════════════════════════════════════════════════════════
# EXECUTION LOOP
# ═══════════════════════════════════════════════════════════════
# The lead monitors TaskList. When tasks become unblocked, spawn teammates.
# This is NOT a polling loop — the lead reacts to SendMessage from teammates.

# Phase 2: Lead runs directly (or spawns a single teammate)
# When Phase 2 task is completed → Phases 3, 4, 5 become unblocked

# Phases 3, 4, 5: Spawn teammates in parallel
Task(
  subagent_type="general-purpose",
  team_name="{{PROJECT_SLUG}}-build",
  name="{{FEATURE_1_SLUG}}-dev",
  mode="plan",  # if require_plan_approval
  model="{{DEFAULT_TEAMMATE_MODEL}}",
  prompt="You are {{FEATURE_1_SLUG}}-dev on team {{PROJECT_SLUG}}-build.
  ... (phase instructions) ..."
)
Task(
  subagent_type="general-purpose",
  team_name="{{PROJECT_SLUG}}-build",
  name="{{FEATURE_2_SLUG}}-dev",
  mode="plan",
  model="{{DEFAULT_TEAMMATE_MODEL}}",
  prompt="You are {{FEATURE_2_SLUG}}-dev on team {{PROJECT_SLUG}}-build.
  ... (phase instructions) ..."
)
Task(
  subagent_type="general-purpose",
  team_name="{{PROJECT_SLUG}}-build",
  name="{{FEATURE_3_SLUG}}-dev",
  mode="plan",
  model="{{DEFAULT_TEAMMATE_MODEL}}",
  prompt="You are {{FEATURE_3_SLUG}}-dev on team {{PROJECT_SLUG}}-build.
  ... (phase instructions) ..."
)
# Lead waits for all 3 to SendMessage completion + TaskUpdate(completed)

# Phase D: Spawn deploy teammate when 3,4,5 complete
# Phase F: Lead runs directly for final sign-off

# ═══════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════
# Send shutdown_request to all remaining teammates
SendMessage(type="shutdown_request", recipient="{{FEATURE_1_SLUG}}-dev", content="Project complete.")
SendMessage(type="shutdown_request", recipient="{{FEATURE_2_SLUG}}-dev", content="Project complete.")
SendMessage(type="shutdown_request", recipient="{{FEATURE_3_SLUG}}-dev", content="Project complete.")
# Wait for shutdown confirmations
TeamDelete()
```

### Swarm Orchestration Pattern

In swarm mode, teams are created and destroyed per wave:

```
{{BLOCK:WAVE}}
# ═══════════════════════════════════════════════════════════════
# WAVE {{WAVE_NUM}}: {{WAVE_DESCRIPTION}}
# ═══════════════════════════════════════════════════════════════

{{IF_WAVE_LEAD_SOLO}}
# Lead runs Phase {{PHASE_ID}} directly via Task tool (no team needed for solo wave)
Task(
  subagent_type="general-purpose",
  description="Phase {{PHASE_ID}}",
  prompt="Execute Phase {{PHASE_ID}}: {{PHASE_TITLE}}. ..."
)
# Verify completion, then proceed to next wave
{{/IF_WAVE_LEAD_SOLO}}

{{IF_WAVE_PARALLEL}}
# 1. CREATE WAVE TEAM
TeamCreate(
  team_name="{{PROJECT_SLUG}}-wave-{{WAVE_NUM}}",
  description="Wave {{WAVE_NUM}}: {{WAVE_DESCRIPTION}}"
)

# 2. CREATE TASKS WITH DEPENDENCIES
{{BLOCK:WAVE_TASK}}
TaskCreate(
  subject="Phase {{N}}: {{PHASE_TITLE}}",
  description="{{PHASE_PURPOSE}}. Done when: {{PHASE_DONE_CRITERIA}}.",
  activeForm="Executing Phase {{N}}: {{PHASE_TITLE}}"
)
{{IF_TASK_DEPENDENCY}}
TaskUpdate(taskId="{{TASK_ID}}", addBlockedBy=["{{BLOCKING_TASK_ID}}"])
{{/IF_TASK_DEPENDENCY}}
{{/BLOCK:WAVE_TASK}}

# 3. SPAWN TEAMMATES (in parallel — all Task calls in one message)
{{BLOCK:TEAMMATE_SPAWN}}
Task(
  subagent_type="{{TEAMMATE_SUBAGENT_TYPE}}",
  team_name="{{PROJECT_SLUG}}-wave-{{WAVE_NUM}}",
  name="{{TEAMMATE_NAME}}",
  {{IF_REQUIRE_PLAN_APPROVAL}}mode="plan",{{/IF_REQUIRE_PLAN_APPROVAL}}
  {{IF_TEAMMATE_MODEL}}model="{{TEAMMATE_MODEL}}",{{/IF_TEAMMATE_MODEL}}
  prompt="You are teammate {{TEAMMATE_NAME}} on team {{PROJECT_SLUG}}-wave-{{WAVE_NUM}}.

YOUR TASK: Execute Phase {{N}}: {{PHASE_TITLE}}.
{{PHASE_PURPOSE}}

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for project state
2. mcp__memory__search_nodes('Decision_') — load ALL resolved technology decisions
3. mcp__memory__search_nodes('{{PHASE_MEMORY_TAG}}') — load phase-specific context
4. TaskList() to find your assigned task. Claim it: TaskUpdate(taskId=..., owner='{{TEAMMATE_NAME}}', status='in_progress')

PHASE INSTRUCTIONS:
{{PHASE_INSTRUCTIONS_INLINE}}

WHEN DONE:
- TaskUpdate(taskId=..., status='completed')
- mcp__memory__create_entities for phase decisions/artifacts
- Update progress.md with your phase results
- /checkpoint:create 'phase{{N}}-{{PHASE_SLUG}}-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase {{N}} complete. {{DONE_SUMMARY}}.', summary='Phase {{N}} done')
"
)
{{/BLOCK:TEAMMATE_SPAWN}}

# 4. MONITOR: Lead waits for messages from teammates
#    Messages arrive automatically — no polling needed.
#    If a teammate goes idle but task incomplete:
SendMessage(
  type="message",
  recipient="{{TEAMMATE_NAME}}",
  content="Your task is not yet complete. Check TaskList() and continue.",
  summary="Continue working"
)

# 5. VERIFY: All tasks in wave completed
TaskList()  # All should show status: "completed"

# 6. SHUTDOWN WAVE
{{BLOCK:TEAMMATE_SHUTDOWN}}
SendMessage(type="shutdown_request", recipient="{{TEAMMATE_NAME}}", content="Wave {{WAVE_NUM}} complete.")
{{/BLOCK:TEAMMATE_SHUTDOWN}}
# Wait for all shutdown confirmations
TeamDelete()
# /checkpoint:create 'wave-{{WAVE_NUM}}-complete'
{{/IF_WAVE_PARALLEL}}
{{/BLOCK:WAVE}}
```

---

## Phase 2: {{PHASE_2_TITLE}}

> **Template note:** Phase 2 is typically the foundational implementation phase (core APIs, auth, data layer).
> All `{{RESOLVED:*}}` references pull from Memory Decision_ entities created in Phase 1.

**Purpose**: {{PHASE_2_PURPOSE}}
**Depends on**: Phase 1 (all technology decisions resolved, gap analysis complete)
**Produces**: {{PHASE_2_PRODUCES}}
**Task ID**: `phase2` (in squad/swarm task list)

### Teammate Prompt (used by squad/swarm; solo uses the same prompt via Task)

```
"Execute {{PROMPT_FILE}} Phase 2: {{PHASE_2_TITLE}}.

Read task_plan.md, findings.md, and progress.md for context and known gaps.
Read Memory for resolved decisions: mcp__memory__search_nodes('Decision_')
Read Memory for Phase 1 results: mcp__memory__search_nodes('assessment')

Use the resolved technology decisions from Memory for all implementation choices:
- Backend framework: read Decision_backend_framework
- Database: read Decision_database
- Cache: read Decision_cache
- (etc. for any field that was a research question)

FOR EACH SERVICE ({{SERVICES_LIST}} -- or read Decision_services if services were researched):

1. READ current state:
   - mcp__serena__get_symbols_overview('{{SERVICE_BASE_PATH}}/<service>/{{SERVICE_ENTRY_FILE}}')
   - Identify all TODO/mock/placeholder code

2. RESEARCH implementation patterns:
   - mcp__pal__apilookup: '{{RESOLVED:backend_framework}} <specific_pattern> production implementation'

3. IMPLEMENT with TDD:
   - Task(subagent_type='backend-development:tdd-orchestrator') - write tests first
   - mcp__serena__replace_symbol_body() - replace mocks with real implementations
   - mcp__serena__insert_after_symbol() - add missing endpoints
   {{BLOCK:IMPLEMENTATION_DETAIL}}
   - {{IMPLEMENTATION_STEP}}
   {{/BLOCK:IMPLEMENTATION_DETAIL}}

4. REVIEW each service:
   - mcp__pal__codereview: production readiness, security, error handling
   - Task(subagent_type='{{SECURITY_AGENT}}') for security review

5. CHECKPOINT after each service:
   - mcp__memory__create_entities for service completion state
   - Update progress.md
   - /checkpoint:create '<service>-complete'

6. INTEGRATION:
   - Verify inter-service communication works
   - Task(subagent_type='full-stack-orchestration:test-automator') for integration tests

DONE WHEN: {{PHASE_2_DONE_CRITERIA}}.
Then: TaskUpdate(status='completed'), SendMessage to lead with summary."
```

---

## Phase N: {{PHASE_N_TITLE}} (Repeatable Feature Phase)

> **Template note:** Copy this section for each feature from your `features` list.
> If the feature's `approach` was a research question, Phase 1 resolved it -- read from Memory.
>
> **Squad/Swarm mode:** This prompt is passed directly to a teammate via `Task(...)`.
> The teammate works autonomously and signals completion via `TaskUpdate` + `SendMessage`.

**Purpose**: {{PHASE_N_PURPOSE}}
**Depends on**: {{PHASE_N_DEPENDS}}
**Produces**: {{PHASE_N_PRODUCES}}
**Task ID**: `phase{{N}}` (blocked by: `{{PHASE_N_DEPENDS_TASK_IDS}}`)

### Teammate Prompt

```
"You are {{TEAMMATE_NAME}} on team {{TEAM_NAME}}.

Execute {{PROMPT_FILE}} Phase {{N}}: {{PHASE_N_TITLE}}.{{IF_CRITICAL}} THIS IS THE CRITICAL PATH.{{/IF_CRITICAL}}

CONTEXT LOADING:
1. Read task_plan.md, findings.md, progress.md for context
2. mcp__memory__search_nodes('Decision_') for all resolved technology decisions
3. mcp__memory__search_nodes('{{PHASE_N_MEMORY_TAG}}') for feature-specific context
4. TaskList() → find and claim your task: TaskUpdate(taskId=..., owner='{{TEAMMATE_NAME}}', status='in_progress')

{{IF_APPROACH_WAS_RESEARCHED}}
RESOLVED APPROACH: Read from Memory: mcp__memory__open_nodes(['Decision_{{FEATURE_CATEGORY}}_approach'])
Use the resolved approach for all implementation decisions in this phase.
{{/IF_APPROACH_WAS_RESEARCHED}}

{{IF_NEEDS_ADDITIONAL_RESEARCH}}
DEEP RESEARCH (parallel):
{{BLOCK:RESEARCH_CALL}}
- {{RESEARCH_TOOL}}: '{{RESEARCH_QUERY}}'
{{/BLOCK:RESEARCH_CALL}}
{{/IF_NEEDS_ADDITIONAL_RESEARCH}}

IMPLEMENTATION:
{{BLOCK:IMPLEMENTATION_SECTION}}
{{SECTION_NUMBER}}. {{SECTION_TITLE}} ({{SECTION_PATH}}):
   - mcp__serena__get_symbols_overview on relevant files
   {{BLOCK:SECTION_STEP}}
   - {{STEP_DESCRIPTION}}
   {{/BLOCK:SECTION_STEP}}
   - mcp__serena__replace_symbol_body / insert_after_symbol for implementation
{{/BLOCK:IMPLEMENTATION_SECTION}}

TESTING:
   - Task(subagent_type='backend-development:tdd-orchestrator') for feature tests
   {{BLOCK:TEST_STEP}}
   - {{TEST_DESCRIPTION}}
   {{/BLOCK:TEST_STEP}}
   - mcp__pal__codereview

FILE OWNERSHIP (parallel safety):
  - You OWN these files (only you edit them): {{OWNED_FILES}}
  - You READ these files (shared, do not edit): {{SHARED_READ_FILES}}
  - If you need a change in a file you don't own, SendMessage to the teammate who owns it.

PLANNING FILES — MANDATORY (read at start, write throughout):
- task_plan.md: Read for phase context. Update YOUR phase status to in_progress at start, complete when done.
- findings.md: Write every significant discovery, decision, or issue as you encounter it (every 2-3 actions).
- progress.md: Log every major action, command output, and test result. This is the audit trail.
- These files are the GROUND TRUTH. If your context window resets, these files are how you recover.

WHEN DONE:
- Update task_plan.md: mark your phase as complete
- Update progress.md: final summary of what was accomplished
- Update findings.md: any final discoveries or open questions for later phases
- TaskUpdate(taskId=..., status='completed')
- mcp__memory__create_entities for {{PHASE_N_MEMORY_TAG}} decisions
- /checkpoint:create 'phase{{N}}-{{PHASE_N_SLUG}}-complete'
- SendMessage(type='message', recipient='team-lead', content='Phase {{N}} complete. {{DONE_SUMMARY}}.', summary='Phase {{N}} done')"
```

---

## Phase Y: Client Integration (optional)

> Include if your project has a separate client. Delete if not applicable.
> If `client_type` was a research question, this phase reads the resolved decision from Memory.

**Purpose**: Connect the client to real backend APIs, replacing all mock data.
**Depends on**: All feature phases
**Task ID**: `phaseY` (blocked by: all feature phase task IDs)

### Teammate Prompt

```
"Execute {{PROMPT_FILE}} Phase Y: Client Integration.

Read task_plan.md, findings.md, progress.md for context.
Read Memory: mcp__memory__search_nodes('Decision_') for resolved technology decisions.
Read Memory: mcp__memory__search_nodes('{{CLIENT_MEMORY_TAG}}') for client context.
TaskList() → claim your task.

IMPLEMENTATION:

1. ANALYZE CURRENT STATE:
   - mcp__serena__list_dir('{{CLIENT_SRC_PATH}}', recursive=True)
   - mcp__serena__get_symbols_overview on key source files
   - mcp__serena__search_for_pattern('mock|fake|dummy|placeholder|TODO') in {{CLIENT_SRC_PATH}}/

2. API CLIENT LAYER:
   - Replace mock API calls with real backend calls
   - Implement: base URL configuration, auth token management, error handling
   - Task(subagent_type='{{CLIENT_AGENT}}') for component integration

{{BLOCK:CLIENT_FEATURE}}
{{FEATURE_NUMBER}}. {{CLIENT_FEATURE_TITLE}}:
   {{BLOCK:CLIENT_FEATURE_STEP}}
   - {{CLIENT_STEP}}
   {{/BLOCK:CLIENT_FEATURE_STEP}}
{{/BLOCK:CLIENT_FEATURE}}

TESTING:
   - Task(subagent_type='{{CLIENT_SECURITY_AGENT}}') for client security audit
   - mcp__pal__codereview on integration code
   - Verify zero mock data remains: mcp__serena__search_for_pattern('mock|fake|dummy') should return nothing

WHEN DONE:
- TaskUpdate(taskId=..., status='completed')
- mcp__memory__create_entities for client integration decisions
- Update progress.md
- /checkpoint:create 'phaseY-client-complete'
- SendMessage(type='message', recipient='team-lead', content='Client integration complete. Zero mock data remaining.', summary='Client done')"
```

---

## Phase D: Deployment & Hardening

> If `deployment` was a research question, this phase reads the resolved decision from Memory.

**Purpose**: Production-grade deployment with SSL, secrets, monitoring, backup, and streamlined startup.
**Depends on**: All feature + client phases
**Task ID**: `phaseD` (blocked by: all feature + client phase task IDs)

### Teammate Prompt

```
"Execute {{PROMPT_FILE}} Phase D: Deployment & Hardening.

Read task_plan.md, findings.md, progress.md for context.
Read Memory: mcp__memory__search_nodes('Decision_') for resolved decisions (especially Decision_deployment).
TaskList() → claim your task.

IMPLEMENTATION:

1. RESEARCH:
   {{BLOCK:DEPLOYMENT_RESEARCH}}
   - {{RESEARCH_TOOL}}: '{{RESEARCH_QUERY}}'
   {{/BLOCK:DEPLOYMENT_RESEARCH}}

2. PRODUCTION CONFIG:
   - Review current deployment configuration
   - Task(subagent_type='deployment-strategies:deployment-engineer') for hardening review
   {{BLOCK:DEPLOYMENT_CHECKLIST}}
   - {{DEPLOYMENT_ITEM}}
   {{/BLOCK:DEPLOYMENT_CHECKLIST}}

3. SSL/TLS:
   {{BLOCK:SSL_STEP}}
   - {{SSL_ITEM}}
   {{/BLOCK:SSL_STEP}}

4. SECRETS MANAGEMENT:
   - Generate script for all required secrets
   - Ensure no hardcoded secrets: mcp__serena__search_for_pattern('password|secret|api_key|token')
   - Task(subagent_type='comprehensive-review:security-auditor') for secrets review

5. MONITORING STACK:
   - Task(subagent_type='observability-monitoring:observability-engineer') for dashboards
   {{BLOCK:MONITORING_ITEM}}
   - {{MONITORING_STEP}}
   {{/BLOCK:MONITORING_ITEM}}

6. BACKUP & RESTORE:
   {{BLOCK:BACKUP_ITEM}}
   - {{BACKUP_STEP}}
   {{/BLOCK:BACKUP_ITEM}}

7. SECURITY HARDENING:
   - Task(subagent_type='comprehensive-review:security-auditor') final infrastructure audit
   - mcp__pal__codereview on deployment configs

WHEN DONE:
- TaskUpdate(taskId=..., status='completed')
- mcp__memory__create_entities for deployment architecture decisions
- Update progress.md
- /checkpoint:create 'phaseD-deployment-complete'
- SendMessage(type='message', recipient='team-lead', content='Deployment hardening complete. SSL, secrets, monitoring, backups all configured.', summary='Deployment done')"
```

---

## Phase F: Testing & Validation (FINAL)

**Purpose**: Comprehensive testing to verify ALL success criteria. Final sign-off.
**Depends on**: All prior phases
**Produces**: All tests passing, load test results, security audit clean, success criteria checklist complete
**Task ID**: `phaseF` (blocked by: phaseD)
**Assigned to**: Lead (always — final sign-off should not be delegated)

### Lead Runs Directly

```
Task(
  subagent_type="general-purpose",
  description="Final validation",
  prompt="Execute {{PROMPT_FILE}} Phase F: Testing & Validation. FINAL PHASE.

Read task_plan.md, findings.md, progress.md for full context.
Read Memory: mcp__memory__read_graph() for all prior decisions and state.

COMPREHENSIVE TESTING:

1. UNIT TESTS:
   - Task(subagent_type='unit-testing:test-automator') for all services
   - Target: >80% code coverage per service

2. INTEGRATION TESTS:
   - Task(subagent_type='full-stack-orchestration:test-automator') for cross-service tests
   {{BLOCK:INTEGRATION_FLOW}}
   - {{FLOW_DESCRIPTION}}
   {{/BLOCK:INTEGRATION_FLOW}}

3. END-TO-END TESTS:
   - Task(subagent_type='full-stack-orchestration:test-automator') for E2E:
   {{BLOCK:E2E_SCENARIO}}
     - {{E2E_STEP}}
   {{/BLOCK:E2E_SCENARIO}}

4. LOAD TESTING:
   - Task(subagent_type='full-stack-orchestration:performance-engineer') for:
   {{BLOCK:LOAD_SCENARIO}}
     - {{LOAD_DESCRIPTION}}
   {{/BLOCK:LOAD_SCENARIO}}
   - Measure: latency p50/p95/p99, throughput, error rate

5. SECURITY TESTING:
   - Task(subagent_type='comprehensive-review:security-auditor') final audit
   - OWASP Top 10 checklist verification

6. FINAL CODE REVIEW:
   - /code-review on all changed files
   - /validate-and-fix for auto-fixable issues
   - mcp__pal__codereview: comprehensive final review
   - mcp__pal__challenge: '{{PROJECT_NAME}} is production-ready for {{TARGET_USERS}} {{GEO_DISTRIBUTION}} users'
   - Task(subagent_type='code-review-ai:architect-review') final architecture review

7. SUCCESS CRITERIA CHECKLIST (verify EVERY item):
    Functional:
    {{BLOCK:FUNCTIONAL_CHECK}}
    - [ ] {{FUNCTIONAL_CRITERION}}
    {{/BLOCK:FUNCTIONAL_CHECK}}

    Infrastructure:
    {{BLOCK:INFRA_CHECK}}
    - [ ] {{INFRA_CRITERION}}
    {{/BLOCK:INFRA_CHECK}}

    Deployment:
    {{BLOCK:DEPLOY_CHECK}}
    - [ ] {{DEPLOY_CRITERION}}
    {{/BLOCK:DEPLOY_CHECK}}

    Performance:
    {{BLOCK:PERF_CHECK}}
    - [ ] {{PERF_CRITERION}}
    {{/BLOCK:PERF_CHECK}}

8. FINAL CHECKPOINT:
    - mcp__memory__create_entities for: test results, benchmarks, security results, criteria status
    - Update progress.md with final status
    - Update task_plan.md marking all phases complete
    - /checkpoint:create 'production-ready'

{{IF_SQUAD_OR_SWARM}}
NOTE: After this phase returns, the lead handles team cleanup (shutdown_request to
remaining teammates + TeamDelete). See Squad/Swarm Orchestration Patterns above.
{{/IF_SQUAD_OR_SWARM}}

DONE WHEN: ALL success criteria checkboxes verified, all tests pass, load tests meet targets, security audit clean, monitoring operational."
)
```

---

## Quick Reference: Execution Sequence

```
PHASE                                    TASK STATUS SIGNAL          ASSIGNED TO
──────────────────────────────────────────────────────────────────────────────────
Step 0: Bootstrap                        TaskCreate (seed)           Lead
Phase 1: Assessment + Tech Selection     TaskUpdate(completed)       Lead / Research team
Phase 2: {{PHASE_2_TITLE}}              TaskUpdate(completed)       Lead / Teammate
{{BLOCK:PHASE_ROW}}
Phase {{N}}: {{PHASE_TITLE}}            TaskUpdate(completed)       Teammate
{{/BLOCK:PHASE_ROW}}
Phase D: Deployment & Hardening          TaskUpdate(completed)       Teammate
Phase F: Testing & Validation (FINAL)    TaskUpdate(completed)       Lead (always)
──────────────────────────────────────────────────────────────────────────────────
                                         ALL TASKS COMPLETED → TeamDelete / Done
```

---

## Between Phases

### Solo Mode

After each Task completes:

1. **Review output** - Check progress.md for what was accomplished
2. **Check findings** - Review findings.md for new discoveries or blockers
3. **Verify decisions** - `mcp__memory__search_nodes('Decision_')` to verify all tech decisions are stored
4. **Verify checkpoint** - Use `/checkpoint:list` to confirm checkpoint was saved
5. **Decide next** - Spawn next Task, or re-run current phase if incomplete

### Squad / Swarm Mode — Between Waves

After all teammates in a wave send completion messages:

1. **Check task list** - `TaskList()` to verify all tasks in the wave are `completed`
2. **Collect teammate findings** - Read Memory entities written by each teammate
3. **Review progress.md** - Each teammate updates this; check for conflicts or gaps
4. **Verify no file conflicts** - If teammates touched overlapping files, review diffs
5. **Resolve cross-phase issues** - If Teammate A's output affects Teammate B's work, resolve before next wave
6. **Shut down wave teammates** (swarm only):
   ```
   SendMessage(type="shutdown_request", recipient="teammate-name", content="Wave N complete.")
   ```
   Wait for shutdown confirmations, then `TeamDelete()`
7. **Checkpoint** - `/checkpoint:create 'wave-{{N}}-complete'`
8. **Decide next** - Start next wave, or re-run failed phases with new teammates

### Handling Teammate Issues

| Symptom | Action |
|---------|--------|
| Teammate goes idle, task incomplete | `SendMessage` with guidance to continue |
| Teammate errors repeatedly | `SendMessage(shutdown_request)`, spawn replacement with adjusted prompt |
| File conflict between teammates | Pause wave, resolve manually, resume remaining teammates |
| Teammate drifts off-task | `SendMessage` with explicit redirect instructions |
| All teammates stuck on shared blocker | Lead investigates, broadcasts solution via `SendMessage(type="broadcast")` |
| Teammate sends plan for approval | Review plan, respond with `SendMessage(type="plan_approval_response")` |

---

## Competing Hypotheses Pattern (Critical Path)

For critical-path features, spawn multiple research teammates to investigate different approaches simultaneously:

```
# Instead of one teammate for Phase 3 (critical path), spawn 3 investigators + 1 challenger:

TeamCreate(team_name="{{PROJECT_SLUG}}-hypothesis", description="Competing approaches for {{CRITICAL_FEATURE}}")

TaskCreate(subject="Investigate Approach A: {{APPROACH_A}}", description="...", activeForm="Researching {{APPROACH_A}}")
TaskCreate(subject="Investigate Approach B: {{APPROACH_B}}", description="...", activeForm="Researching {{APPROACH_B}}")
TaskCreate(subject="Challenge both approaches", description="...", activeForm="Challenging approaches")
TaskUpdate(taskId="challenge_id", addBlockedBy=["approach_a_id", "approach_b_id"])

# Spawn investigators in parallel
Task(
  subagent_type="Explore",
  team_name="{{PROJECT_SLUG}}-hypothesis",
  name="approach-a-investigator",
  prompt="Investigate approach A for {{CRITICAL_FEATURE}}: {{APPROACH_A_DESCRIPTION}}.
  Research viability, document trade-offs, store findings in Memory.
  TaskUpdate(completed) + SendMessage to lead when done."
)
Task(
  subagent_type="Explore",
  team_name="{{PROJECT_SLUG}}-hypothesis",
  name="approach-b-investigator",
  prompt="Investigate approach B for {{CRITICAL_FEATURE}}: {{APPROACH_B_DESCRIPTION}}.
  Research viability, document trade-offs, store findings in Memory.
  TaskUpdate(completed) + SendMessage to lead when done."
)

# After A and B complete, challenger runs automatically (unblocked by dependency)
Task(
  subagent_type="general-purpose",
  team_name="{{PROJECT_SLUG}}-hypothesis",
  name="challenger",
  prompt="You are the devil's advocate. Read Memory entities from approach-a-investigator
  and approach-b-investigator. Challenge both. Find weaknesses. Recommend which
  approach to proceed with and why.
  TaskUpdate(completed) + SendMessage to lead with recommendation."
)

# After challenge round: lead picks winner, shuts down hypothesis team,
# spawns implementation teammate with the chosen approach.
```

---

## Dependencies Between Phases

### Dependency Graph (expressed as TaskUpdate blockedBy)

```
Step 0 ─── mandatory ──→ Phase 1
Phase 1 ── mandatory ──→ Phase 2  (all tech decisions must be resolved)
{{BLOCK:DEPENDENCY}}
{{FROM}} ── {{TYPE}} ──→ {{TO}}
{{/BLOCK:DEPENDENCY}}

Critical path: {{CRITICAL_PATH}}
Parallelizable: {{PARALLEL_PHASES}}
```

### Task Dependency Setup (Squad Mode)

```
# These TaskUpdate calls establish the dependency graph:
# Phase 2 is unblocked after Phase 1 completes
TaskUpdate(taskId="phase2", addBlockedBy=["phase1"])

# Feature phases are unblocked after Phase 2
TaskUpdate(taskId="phase3", addBlockedBy=["phase2"])
TaskUpdate(taskId="phase4", addBlockedBy=["phase2"])
TaskUpdate(taskId="phase5", addBlockedBy=["phase2"])

# Deployment requires all features
TaskUpdate(taskId="phaseD", addBlockedBy=["phase3", "phase4", "phase5"])

# Final validation requires deployment
TaskUpdate(taskId="phaseF", addBlockedBy=["phaseD"])
```

### Wave Mapping (Swarm Mode)

```
┌──────────┬──────────────────────────────────────────┬────────────────┐
│  Wave    │  Phases                                  │  Mode          │
├──────────┼──────────────────────────────────────────┼────────────────┤
│  Wave 0  │  Step 0, Phase 1                         │  lead-solo     │
│  Wave 1  │  Phase 2                                 │  lead-solo     │
{{BLOCK:WAVE_ROW}}
│  Wave {{WAVE_NUM}}  │  {{WAVE_PHASES}}              │  {{WAVE_MODE}} │
{{/BLOCK:WAVE_ROW}}
│  Wave F  │  Phase F (Final Validation)              │  lead-solo     │
└──────────┴──────────────────────────────────────────┴────────────────┘

Teammate count per parallel wave:
{{BLOCK:WAVE_COUNT}}
  Wave {{WAVE_NUM}}: {{TEAMMATE_COUNT}} teammates ({{TEAMMATE_NAMES}})
{{/BLOCK:WAVE_COUNT}}
```

### File Ownership Matrix (Parallel Safety)

> CRITICAL: Two teammates must NEVER edit the same file simultaneously.
> Define file ownership before spawning parallel teammates.
> Include ownership in each teammate's prompt.

```
{{BLOCK:FILE_OWNERSHIP}}
Teammate: {{TEAMMATE_NAME}} (Phase {{N}})
  Owns (exclusive edit): {{FILE_PATHS}}
  Reads (shared, no edit): {{SHARED_READ_PATHS}}
  Coordination: If needs changes in shared files, SendMessage to owning teammate
{{/BLOCK:FILE_OWNERSHIP}}
```

---

## Phase Design Checklist

### All Topologies

- [ ] **Planning files read** - `Read task_plan.md, findings.md, progress.md` at START of phase
- [ ] **Planning files write** - Write findings.md every 2-3 actions; update progress.md with actions/results
- [ ] **Decision read** - `mcp__memory__search_nodes('Decision_')` for resolved tech choices
- [ ] **Research step** - At least one of: Octagon, Brave, PAL apilookup
- [ ] **Serena code exploration** - `get_symbols_overview`, `find_symbol` before modifying
- [ ] **Implementation** - Using `replace_symbol_body`, `insert_after_symbol`, or agent tasks
- [ ] **Review** - `mcp__pal__codereview` or Task(security-auditor)
- [ ] **Testing** - TDD orchestrator or test-automator agent
- [ ] **Planning files close** - Update task_plan.md phase status to complete, final progress.md entry
- [ ] **Checkpoint** - Memory entity + `/checkpoint:create`
- [ ] **Done criteria** - Clear, testable conditions for when the phase is complete

### Squad / Swarm Additions

- [ ] **Task claim** - `TaskUpdate(taskId=..., owner='name', status='in_progress')` at start
- [ ] **File ownership** - Phase only edits files it owns (no cross-teammate conflicts)
- [ ] **Task completion** - `TaskUpdate(status='completed')` when done criteria met
- [ ] **Lead notification** - `SendMessage(type='message', recipient='team-lead', ...)` with summary
- [ ] **Shutdown readiness** - Teammate handles `shutdown_request` gracefully after completion
- [ ] **Standalone context** - Phase prompt includes enough context to work without conversation history
- [ ] **Plan approval** - If `require_plan_approval: true`, teammate uses `mode='plan'`

---

## Agent Selection Guide

| Need                          | Agent / Tool                                              |
|-------------------------------|-----------------------------------------------------------|
| TDD for backend               | `backend-development:tdd-orchestrator`                    |
| FastAPI implementation         | `python-development:fastapi-pro`                          |
| Django implementation          | `python-development:django-pro`                           |
| Express/Node.js backend        | `javascript-typescript:javascript-pro`                    |
| Go backend                     | `systems-programming:golang-pro`                          |
| React/Next.js frontend         | `frontend-mobile-development:frontend-developer`          |
| Mobile (RN/Flutter)            | `frontend-mobile-development:mobile-developer`            |
| Security audit                 | `comprehensive-review:security-auditor`                   |
| Backend API security           | `backend-api-security:backend-security-coder`             |
| Frontend security              | `frontend-mobile-security:frontend-security-coder`        |
| Database optimization          | `database-cloud-optimization:database-optimizer`          |
| PostgreSQL schema design       | `database-design:sql-pro`                                 |
| Performance/load testing       | `full-stack-orchestration:performance-engineer`           |
| Deployment hardening           | `deployment-strategies:deployment-engineer`                |
| Kubernetes architecture        | `kubernetes-operations:kubernetes-architect`               |
| Terraform/IaC                  | `cloud-infrastructure:terraform-specialist`                |
| Observability/monitoring       | `observability-monitoring:observability-engineer`          |
| Architecture review            | `code-review-ai:architect-review`                         |
| Cross-service tests            | `full-stack-orchestration:test-automator`                  |
| Unit tests                     | `unit-testing:test-automator`                              |
| Debugging                      | `error-debugging:debugger`                                 |
| Deep analysis                  | `mcp__pal__thinkdeep`                                      |
| Multi-model validation         | `mcp__pal__consensus`                                      |
| Assumption challenging         | `mcp__pal__challenge`                                      |
| Deep research                  | `mcp__octagon-deep-research-mcp__octagon-deep-research-agent` |
| Web search                     | `mcp__brave-search__brave_web_search`                      |
| **Team Primitives**            |                                                            |
| Create team workspace          | `TeamCreate(team_name=..., description=...)`               |
| Create work item               | `TaskCreate(subject=..., description=..., activeForm=...)` |
| Set dependencies               | `TaskUpdate(taskId=..., addBlockedBy=[...])`               |
| Check progress                 | `TaskList()`                                               |
| Spawn teammate                 | `Task(subagent_type=..., team_name=..., name=..., prompt=...)` |
| Direct message                 | `SendMessage(type="message", recipient=..., content=...)` |
| Broadcast to all               | `SendMessage(type="broadcast", content=...)` (use sparingly) |
| Graceful shutdown              | `SendMessage(type="shutdown_request", recipient=...)` |
| Approve teammate plan          | `SendMessage(type="plan_approval_response", ...)` |
| Destroy team                   | `TeamDelete()` |

---

## When to Use Which Topology

| Scenario | Recommended Topology | Why |
|----------|---------------------|-----|
| 0-2 features, tight dependencies | `solo` | Team overhead exceeds benefit |
| 3+ features, some parallelizable | `squad` | One team, parallel when possible |
| 5+ features, clear boundaries | `swarm` | Maximum throughput, full isolation |
| Research-heavy (8+ open questions) | `swarm` for Phase 1 | Parallel research with competing hypotheses |
| Single developer reviewing output | `solo` | Easier to follow and review |
| CI/CD or automated execution | `swarm` | Maximum throughput, minimal human review |
| Long-running project, persistent team | `squad` | Team context preserved across waves |
| Short sprint, disposable context | `swarm` | Clean slate per wave |

### Token Cost Comparison

| Topology | Relative Cost | Throughput | Complexity |
|----------|--------------|------------|------------|
| `solo` | 1x (baseline) | Serial | Minimal |
| `squad` | ~1.5-2x | Parallel within waves | Moderate (task dependencies) |
| `swarm` | ~2-4x | Maximum parallel | High (team lifecycle management) |

---

# Appendix: Worked Examples

---

## Example A: "I just have a goal" (Maximum research, swarm topology)

```yaml
project_name: "CollabDocs"
project_slug: "collab-docs"
prompt_file: "PROMPT_COLLAB_DOCS.md"
goal_summary: "Build a production-ready collaborative document editor like Google Docs Lite for a 20-person team"
team_topology: "swarm"

tech_stack:
  backend_framework:
    research: "What backend framework is best for real-time collaborative editing with OT/CRDT support?"
    constraints: ["Must handle WebSocket connections efficiently", "Good ecosystem for CRDT libraries"]
  # ... (10 total research fields)

team_config:
  team_name: "collab-docs-build"
  delegate_lead: true
  require_plan_approval: true
  default_teammate_model: "sonnet"
  waves:
    - wave: 0
      mode: "lead-solo"
      phases: ["step0"]
    - wave: 1
      mode: "parallel"
      phases: ["research-backend", "research-frontend", "research-data", "gap-analysis"]
      teammates:
        - name: "backend-researcher"
          phase: "research-backend"
          subagent_type: "Explore"
        - name: "frontend-researcher"
          phase: "research-frontend"
          subagent_type: "Explore"
        - name: "data-researcher"
          phase: "research-data"
          subagent_type: "Explore"
        - name: "gap-analyst"
          phase: "gap-analysis"
          subagent_type: "Explore"
    - wave: 2
      mode: "lead-solo"
      phases: ["phase2"]  # Foundation
    - wave: 3
      mode: "parallel"
      phases: ["phase3-crdt", "phase4-docs", "phase5-perms"]
      teammates:
        - name: "crdt-dev"
          phase: "phase3-crdt"
          subagent_type: "general-purpose"
        - name: "docs-dev"
          phase: "phase4-docs"
          subagent_type: "general-purpose"
        - name: "perms-dev"
          phase: "phase5-perms"
          subagent_type: "general-purpose"
    - wave: 4
      mode: "parallel"
      phases: ["phaseD", "phaseF-prep"]
      teammates:
        - name: "deploy-engineer"
          phase: "phaseD"
          subagent_type: "general-purpose"
        - name: "test-engineer"
          phase: "phaseF-prep"
          subagent_type: "general-purpose"
    - wave: 5
      mode: "lead-solo"
      phases: ["phaseF"]
```

**What happens:** Wave 1 spawns 4 parallel research teammates, each resolving a subset of the 10 research questions. The lead synthesizes their findings, asks the user to confirm decisions, and stores `Decision_*` entities. Wave 3 runs 3 feature teammates in parallel. The critical-path CRDT phase could optionally use the competing hypotheses pattern before Wave 3.

---

## Example B: "I know some things" (Mixed knowledge, squad topology)

```yaml
project_name: "ModelServe"
project_slug: "model-serve"
team_topology: "squad"

tech_stack:
  backend_framework:
    value: "FastAPI"       # Known
  deployment:
    research: "Compare Kubernetes vs Docker Compose vs managed services for ML model serving"

team_config:
  team_name: "model-serve-build"
  delegate_lead: true
  require_plan_approval: true
  waves:
    - wave: 0
      mode: "lead-solo"
      phases: ["step0", "phase1", "phase2"]
    - wave: 1
      mode: "parallel"
      phases: ["phase3-registry", "phase3-monitoring"]
    - wave: 2
      mode: "parallel"
      phases: ["phase4-inference", "phase4-abtesting"]
    - wave: 3
      mode: "lead-solo"
      phases: ["phaseD", "phaseF"]
```

**What happens:** One persistent team. All tasks created upfront with dependencies. Lead runs early phases directly. Feature pairs run in parallel as teammates. 5 research fields resolved in Phase 1. Team persists until final cleanup.

---

## Example C: "I know everything" (Minimal research, solo topology)

```yaml
project_name: "Voice Chat"
project_slug: "voice-chat"
team_topology: "solo"
# No team_config needed — all phases run as individual Task() calls

tech_stack:
  backend_framework:
    value: "FastAPI"
  # ... all concrete values
```

**What happens:** Lead spawns one `Task(subagent_type="general-purpose")` per phase, sequentially. No teams, no task lists, no messaging. Simplest possible execution. The template degrades gracefully to a sequential task pipeline.

---

## Research Complexity Quick Reference

| Open research fields | Phase 1 approach | Recommended topology |
|----------------------|-------------------|---------------------|
| 0                    | Pure gap analysis  | `solo`              |
| 1-3                  | Lead researches directly | `solo` or `squad` |
| 4-7                  | Lead + 1-2 research helpers | `squad`        |
| 8+                   | Parallel research team | `swarm`           |

| Feature count | Dependencies | Recommended topology | Why |
|---------------|-------------|---------------------|-----|
| 1-2           | Any         | `solo`               | Team overhead exceeds benefit |
| 3-4           | Tight chain | `squad` (serial)     | Can't parallelize dependent phases |
| 3-4           | Some parallel| `squad` (parallel)  | One team, parallel where possible |
| 5+            | Mostly independent | `swarm`         | Maximum throughput |
