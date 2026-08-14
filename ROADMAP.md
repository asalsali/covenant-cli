# Roadmap

covenant-cli is becoming the governance layer for multi-agent Python projects. Not another framework for building agents -- a framework for governing them. Every agent SDK gives you orchestration, tool use, and prompt management. None of them answer the questions that matter after your first demo: what did the agent do? Did it work? What should the next run know? What is the project learning over time? covenant-cli answers these questions structurally, embedded in code, regardless of which SDK you chose. When it is done, governance will be as natural to agent development as testing is to software engineering.

---

## Current State (v0.5.0)

Eight commands across three SDK adapters:

| Command | Purpose |
|---------|---------|
| `covenant init` | Scaffold a governed project with SDK choice (OpenAI, CrewAI, LangGraph) |
| `covenant add-service` | Add a governed service with working agent code, typed schemas, exit reports |
| `covenant status` | Project health dashboard: services, runs, tokens, memos, consolidation |
| `covenant remember` | Search exit reports, memos, and consolidated summaries by keyword |
| `covenant audit` | 10-point structural health check with scoring |
| `covenant memo` | Cross-service communication (send/list/read) |
| `covenant consolidate` | Distill exit reports into summaries with optional archiving |
| `covenant doctor` | Environment validation: Python, SDK, API keys, structure, governance |

The governance layer ships with 18 rules in GOVERNANCE.md, convention rules for Cursor and Claude Code (.mdc files), Pydantic-typed I/O schemas, automatic exit report writing, usage tracking, and branded terminal output.

---

## User Journeys

Six paths through covenant-cli -- from first install to multi-service coordination.

---

### Journey 1: Solo Developer -- First Project

**You are:** A developer who builds with AI agents and just realized you have no idea what your agents did last Tuesday.
**You want:** A governed project scaffold where every agent run leaves a trail.

#### Install and scaffold

```
$ pip install covenant-cli
$ covenant init my-project --sdk openai
```

```
  +-------------------------------+
  |                               |
  |     .o.     .o.               |
  |    o   'o.o'   o              |
  |     'o'     'o'               |
  |                               |
  |    C O V E N A N T            |
  |                               |
  |    Governed agents.            |
  |    From the first line.        |
  |                               |
  +-------------------------------+

  my-project/
  +  GOVERNANCE.md
  +  pyproject.toml
  +  README.md
  +  .env.example
  +  src/__init__.py
  +  src/main.py
  +  registry/agents.json
  +  memory/inheritance/README.md
  +  memory/memos/README.md
  +  .cursor/rules/governance.mdc
  +  .cursor/rules/agent-patterns.mdc
  +  .claude/rules/governance.mdc
  +  .claude/rules/agent-patterns.mdc

  +-------------------------------+
  |  Next Steps                   |
  |                               |
  |  Project created.             |
  |                               |
  |    cd my-project              |
  |    pip install -e .           |
  |    covenant add-service       |
  |        my-first-agent         |
  |    covenant status            |
  |                               |
  |  Read GOVERNANCE.md           |
  |    -- it's the law.           |
  +-------------------------------+
```

**What's happening:** The CLI creates a complete project structure. `GOVERNANCE.md` contains 18 rules. `registry/agents.json` tracks every service. `memory/inheritance/` is where exit reports accumulate. Convention rules for your IDE are already in place -- governance is enforced at development time, not just at review time.

#### Add a service

```
$ cd my-project
$ covenant add-service research-agent --sdk openai
```

```
  services/research_agent/
  +  __init__.py
  +  manager.py
  +  tools.py
  +  agents/__init__.py
  +  agents/example_agent.py
  +  schemas/__init__.py
  +  schemas/types.py
  +  memory/README.md

  +-------------------------------+
  |  Next Steps                   |
  |                               |
  |  Service 'research_agent'     |
  |  registered.                  |
  |                               |
  |  1. Edit services/            |
  |     research_agent/agents/    |
  |     example_agent.py          |
  |  2. Define types in services/ |
  |     research_agent/schemas/   |
  |     types.py                  |
  |  3. Wire agents in services/  |
  |     research_agent/manager.py |
  |  4. Run: covenant status      |
  |                               |
  |  The manager writes exit      |
  |  reports automatically.       |
  +-------------------------------+
```

**What's happening:** The service comes with a manager that writes exit reports on every run, an example agent wired to the OpenAI Agents SDK, Pydantic schemas for typed I/O, and a tools file. The service is registered in `registry/agents.json` before it runs a single line of code.

#### Edit, run, observe

Open `agents/example_agent.py`, replace the placeholder with your agent logic. Run the service. The manager handles exit report writing automatically.

```
$ covenant status
```

```
  +-------------------------------+
  |  Project Status               |
  |                               |
  |  my-project                   |
  |  Governance: active           |
  |  Services:   1                |
  |  Updated:    2026-08-13...    |
  +-------------------------------+

  Services
  +------------------+------+--------+----------------------+
  | Name             | Path | Status | Last Run             |
  +------------------+------+--------+----------------------+
  | research-agent   | ...  | active | 2026-08-13T10:15:00Z |
  +------------------+------+--------+----------------------+

  Recent Exit Reports
  +------------------+-----------+----------+----------------------+
  | Service          | Status    | Duration | Timestamp            |
  +------------------+-----------+----------+----------------------+
  | research-agent   | completed | 9.8s     | 2026-08-13T10:15:00Z |
  +------------------+-----------+----------+----------------------+

  Tokens: 2,340 total  |  Cost: $0.02
```

**What's happening:** Your first run produced an exit report. The status dashboard shows it. Token usage is tracked. From this point forward, every run adds to the project's memory.

#### Read what the system learned

```
$ covenant remember
```

```
  +-------------------------------+
  |  Exit Reports                 |
  |                               |
  |  Showing 1 of 1 reports       |
  +-------------------------------+

  research_agent  2026-08-13T10:15:00Z  completed  9.8s
    Worked:  First successful end-to-end research run
    Failed:  --
    Recommends:  Increase result limit from 5 to 20
```

**What's happening:** The `remember` command surfaces what the system knows. One run, one report, one recommendation. Over time, this becomes a searchable institutional memory. The next agent run can read what this one learned.

**Where this leads:** After several more runs, you will have a trail of exit reports showing what improved, what failed, and what the system recommends. This trail is the difference between an agent that works once and one you can trust.

**Commands used:** `init`, `add-service`, `status`, `remember`

---

### Journey 2: Iterative Improvement Loop

**You are:** A developer with a working service, running it daily.
**You want:** To see patterns emerge -- what keeps failing, what is improving, what the system has learned.

#### Run, check, learn

After several runs, exit reports accumulate in `memory/inheritance/`. Each records what worked, what failed, and what the next run should know.

```
$ covenant remember
```

```
  +-------------------------------+
  |  Exit Reports                 |
  |                               |
  |  Showing 4 of 4 reports       |
  +-------------------------------+

  research_agent  2026-08-13T14:30:00Z  completed  12.3s
    Worked:  API pagination handled correctly
    Failed:  --
    Recommends:  Add retry logic for rate-limited endpoints

  research_agent  2026-08-13T11:15:00Z  completed  18.7s
    Worked:  Source deduplication removed 12 duplicates
    Failed:  --
    Recommends:  Cache dedupe hashes between runs

  research_agent  2026-08-12T22:00:00Z  failed     45.1s
    Worked:  --
    Failed:  Timeout on arxiv.org after 30s
    Recommends:  Add configurable timeout with fallback sources

  research_agent  2026-08-12T16:00:00Z  completed  9.8s
    Worked:  First successful end-to-end research run
    Failed:  --
    Recommends:  Increase result limit from 5 to 20
```

**What's happening:** You can read the arc: first success, then a timeout failure, then the service improved to handle deduplication and pagination. The recommendation from the failed run ("add configurable timeout") is information you can act on now.

#### Search for specific patterns

```
$ covenant remember "timeout"
```

```
  +-------------------------------+
  |  Exit Reports matching        |
  |  'timeout'                    |
  |                               |
  |  Showing 1 of 1 reports       |
  +-------------------------------+

  research_agent  2026-08-12T22:00:00Z  failed  45.1s
    Worked:  --
    Failed:  Timeout on arxiv.org after 30s
    Recommends:  Add configurable timeout with fallback sources
```

#### Consolidate the learnings

After enough runs, consolidate to distill exit reports into a summary:

```
$ covenant consolidate
```

```
  +-------------------------------+
  |  Consolidation Complete       |
  |                               |
  |  Reports distilled:  4        |
  |  Summary written to:          |
  |  memory/inheritance/          |
  |    consolidated-2026-08-13.md |
  |                               |
  |  Key patterns:                |
  |  - API timeout handling       |
  |    needed across services     |
  |  - Deduplication logic        |
  |    working, cache recommended |
  +-------------------------------+
```

**What's happening:** Consolidation distills individual exit reports into compiled summaries. The next time you run `covenant remember`, consolidated summaries rank higher than individual reports (compiled-truth boost). The memory grows in wisdom, not volume.

#### Verify health

```
$ covenant status
```

The status dashboard now shows token totals per service, the date of last consolidation, and any warnings. If a service is degrading -- taking longer, failing more often -- the dashboard surfaces it.

**Where this leads:** The iterative loop becomes your daily workflow. Run the service, check status, search for patterns, consolidate when memory gets long. Each cycle makes the project smarter.

**Commands used:** `remember`, `consolidate`, `status`

---

### Journey 3: Debugging a Production Failure

**You are:** A developer whose agent service just failed in a way you have not seen before. Or have you?
**You want:** To understand whether this is new, whether it has happened before, and what the system already knows about fixing it.

#### The failure

Your summarizer service fails mid-run. The manager writes a partial exit report before exiting.

#### Search for the failure

```
$ covenant remember --service summarizer --failed
```

```
  +-------------------------------+
  |  Exit Reports matching        |
  |  filters                      |
  |                               |
  |  Showing 2 of 2 reports       |
  +-------------------------------+

  summarizer  2026-08-13T15:00:00Z  failed  62.4s
    Worked:  Input parsing completed
    Failed:  OpenAI API returned 429 (rate limited) on chunk 14 of 20
    Recommends:  Add exponential backoff; split large inputs into smaller batches

  summarizer  2026-08-11T09:30:00Z  failed  58.1s
    Worked:  --
    Failed:  OpenAI API returned 429 (rate limited) on chunk 8 of 15
    Recommends:  Implement rate limit handling before scaling input size
```

**What's happening:** This is not new. The same rate-limiting failure happened four days ago, and the system recommended a fix that was never implemented. The institutional memory caught the pattern.

#### Search across all services

```
$ covenant remember "rate limit"
```

```
  +-------------------------------+
  |  Exit Reports matching        |
  |  'rate limit'                 |
  |                               |
  |  Showing 3 of 3 reports       |
  +-------------------------------+

  summarizer  2026-08-13T15:00:00Z  failed  62.4s
    Worked:  Input parsing completed
    Failed:  OpenAI API returned 429 (rate limited) on chunk 14 of 20
    Recommends:  Add exponential backoff; split large inputs into smaller batches

  summarizer  2026-08-11T09:30:00Z  failed  58.1s
    Worked:  --
    Failed:  OpenAI API returned 429 (rate limited) on chunk 8 of 15
    Recommends:  Implement rate limit handling before scaling input size

  research_agent  2026-08-10T20:00:00Z  completed  34.2s
    Worked:  Retry with backoff handled 3 rate-limit responses
    Failed:  --
    Recommends:  Extract retry logic into shared tools.py
```

**What's happening:** The cross-service search reveals that a sibling service already solved this problem. The research agent has retry logic with backoff, and it recommended extracting it to `tools.py` for shared use. The fix exists in your codebase -- you just need to share it.

#### Run an audit

```
$ covenant audit
```

```
  +-------------------------------+
  |  Audit Results                |
  |                               |
  |  Score: 7/10                  |
  +-------------------------------+

  [PASS]  GOVERNANCE.md exists and is not empty
  [PASS]  Registry is valid JSON with required fields
  [PASS]  All registered services have directory on disk
  [WARN]  Service 'summarizer' has 2 failed runs without fix
  [PASS]  Exit reports have required schema fields
  [PASS]  Memory directories exist
  [PASS]  Convention rules present for at least one IDE
  [WARN]  No consolidation in 7+ days
  [PASS]  Token usage tracking active
  [WARN]  Shared tools.py has no retry utilities
```

**What's happening:** The audit gives you a structural health score and surfaces specific issues. The warning about the summarizer's repeated failures and the missing shared retry logic confirms what the exit reports already told you.

**The debugging flow:**

1. `covenant remember --failed` -- what failed recently?
2. `covenant remember "<error keyword>"` -- has this happened before?
3. Read the recommendations -- has the system already told you how to fix this?
4. Check other services -- has a sibling already solved this?
5. Fix the issue, run again, watch the next exit report confirm the fix

**Commands used:** `remember`, `audit`, `status`

---

### Journey 4: Team Onboarding

**You are:** A new team member who just cloned a governed project. You have never used covenant-cli.
**You want:** To understand the project structure, know what the team has learned, and find where to start.

#### Validate your environment

```
$ covenant doctor
```

```
  +-------------------------------+
  |  Environment Check            |
  +-------------------------------+

  [PASS]  Python 3.11.4
  [PASS]  openai SDK installed (1.35.0)
  [PASS]  OPENAI_API_KEY set
  [PASS]  registry/agents.json valid
  [PASS]  GOVERNANCE.md present (18 rules)
  [PASS]  memory/inheritance/ exists
  [PASS]  memory/memos/ exists
  [PASS]  .cursor/rules/ present (2 rule files)
  [PASS]  .claude/rules/ present (2 rule files)
  [PASS]  3 services scaffolded correctly

  All checks passed. You're ready to develop.
```

**What's happening:** Before you write a line of code, `doctor` confirms your environment is correctly set up. SDK installed, API key present, project structure intact, IDE rules loaded. If anything were missing, the output would tell you exactly what to fix.

#### Orient yourself

```
$ covenant status
```

```
  +-------------------------------+
  |  Project Status               |
  |                               |
  |  our-agent-project            |
  |  Governance: active           |
  |  Services:   3                |
  |  Updated:    2026-08-12...    |
  +-------------------------------+

  Services
  +------------------+------+--------+----------------------+
  | Name             | Path | Status | Last Run             |
  +------------------+------+--------+----------------------+
  | research-agent   | ...  | active | 2026-08-12T14:30:00Z |
  | summarizer       | ...  | active | 2026-08-12T13:00:00Z |
  | report-writer    | ...  | active | 2026-08-12T11:00:00Z |
  +------------------+------+--------+----------------------+

  Recent Exit Reports
  +------------------+-----------+----------+----------------------+
  | Service          | Status    | Duration | Timestamp            |
  +------------------+-----------+----------+----------------------+
  | research-agent   | completed | 12.3s    | 2026-08-12T14:30:00Z |
  | summarizer       | completed | 3.2s     | 2026-08-12T13:00:00Z |
  | report-writer    | completed | 8.1s     | 2026-08-12T11:00:00Z |
  +------------------+-----------+----------+----------------------+

  Tokens: 48,210 total  |  Last consolidation: 2026-08-10
  Unread memos: 1
```

**What's happening:** Without reading documentation, you know the project has three services, all running recently, all successful. You can see token consumption, the last consolidation date, and that there is an unread memo waiting.

#### Run the audit

```
$ covenant audit
```

```
  +-------------------------------+
  |  Audit Results                |
  |                               |
  |  Score: 9/10                  |
  +-------------------------------+

  [PASS]  GOVERNANCE.md exists and is not empty
  [PASS]  Registry is valid JSON with required fields
  [PASS]  All registered services have directory on disk
  [PASS]  All services have recent exit reports
  [PASS]  Exit reports have required schema fields
  [PASS]  Memory directories exist
  [PASS]  Convention rules present for both Cursor and Claude Code
  [PASS]  Consolidation within last 7 days
  [PASS]  Token usage tracking active
  [WARN]  1 unread memo older than 3 days
```

**What's happening:** The audit gives you a structural health score. A 9/10 means this project is well-governed. The single warning about the unread memo tells you there is a cross-service message you should read.

#### Search before you build

Suppose you are tasked with adding caching to the research agent:

```
$ covenant remember "cache"
```

```
  +-------------------------------+
  |  Exit Reports matching        |
  |  'cache'                      |
  |                               |
  |  Showing 2 of 2 reports       |
  +-------------------------------+

  research_agent  2026-08-09T11:15:00Z  completed  18.7s
    Worked:  Source deduplication removed 12 duplicates
    Failed:  --
    Recommends:  Cache dedupe hashes between runs

  research_agent  2026-08-05T16:00:00Z  completed  22.1s
    Worked:  --
    Failed:  Redundant API calls for previously fetched sources
    Recommends:  Implement local cache for fetched URLs
```

**What's happening:** Two prior runs already identified the need for caching and gave specific recommendations. You are not starting from scratch. You are building on what the system has already learned.

**The onboarding flow:**

1. `covenant doctor` -- is my environment ready?
2. `covenant audit` -- is the project healthy?
3. `covenant status` -- what services exist, what is their state?
4. `covenant remember "<my task>"` -- what does the system already know about what I am building?
5. Read GOVERNANCE.md -- what are the rules?

**Commands used:** `doctor`, `audit`, `status`, `remember`

---

### Journey 5: Multi-Service Coordination

**You are:** A developer managing three services that need to share findings across boundaries.
**You want:** Services to learn from each other without manual copy-pasting of learnings.

#### The setup

You have three services in one project: `research-agent` (gathers data), `analyzer` (processes data), and `report-writer` (generates reports). The analyzer keeps failing on malformed input from the research agent.

#### Share findings via memos

The analyzer's exit report notes the problem. You send a memo to document it for the research agent's next development cycle:

```
$ covenant memo send \
    --from analyzer \
    --to research-agent \
    --subject "Malformed output in source_urls field" \
    --body "Exit report 2026-08-14T09:00 shows source_urls contains
    duplicates and null entries. The analyzer skips nulls but duplicates
    cause double-processing. Recommend: deduplicate and filter nulls
    before writing output."
```

```
  +-------------------------------+
  |  Memo Sent                    |
  |                               |
  |  From:    analyzer            |
  |  To:      research-agent      |
  |  Subject: Malformed output    |
  |           in source_urls      |
  |           field               |
  |  Stored:  memory/memos/       |
  |    analyzer-to-research_      |
  |    agent-20260814.md          |
  +-------------------------------+
```

#### Check for memos

Later, when you are working on the research agent, check for messages:

```
$ covenant memo list
```

```
  +-------------------------------+
  |  Memos                        |
  |                               |
  |  Showing 2 memos              |
  +-------------------------------+

  [unread]  analyzer -> research-agent  2026-08-14
    Subject: Malformed output in source_urls field

  [read]    research-agent -> report-writer  2026-08-10
    Subject: New fields available in output schema
```

```
$ covenant memo read analyzer-to-research_agent-20260814
```

**What's happening:** Memos are structured, asynchronous, cross-service communication. They live in `memory/memos/` and are searchable via `covenant remember`. No Slack messages lost in a thread. No comments buried in a PR. The finding is in the project's memory, permanently.

#### Search across everything

```
$ covenant remember "duplicate"
```

```
  +-------------------------------+
  |  Results matching             |
  |  'duplicate'                  |
  |                               |
  |  Showing 3 results            |
  +-------------------------------+

  [memo]  analyzer -> research-agent  2026-08-14
    ...duplicates cause double-processing...

  [consolidated]  2026-08-13 summary
    ...deduplication removed 12 duplicates...

  [exit report]  research_agent  2026-08-09T11:15:00Z
    Worked:  Source deduplication removed 12 duplicates
    Recommends:  Cache dedupe hashes between runs
```

**What's happening:** The `remember` command searches across exit reports, memos, and consolidated summaries. The consolidated summary ranks highest (compiled-truth boost). You get the full picture: the memo flagging the problem, the consolidated learning, and the original exit report that first addressed deduplication.

#### Consolidate the project-wide view

```
$ covenant consolidate
```

Consolidation distills all recent exit reports across all services into a single summary. The cross-service patterns become visible: the analyzer's failures correlate with the research agent's output quality. The consolidated summary captures this relationship.

**Where this leads:** Multi-service projects build up a shared institutional memory. Memos handle targeted communication. Consolidation handles the big picture. `remember` searches everything. No service is an island.

**Commands used:** `memo send`, `memo list`, `memo read`, `remember`, `consolidate`

---

### Journey 6: Switching SDKs

**You are:** A developer who started with the OpenAI Agents SDK but needs to add a service using CrewAI (different cost model, better for certain workflows).
**You want:** To add a CrewAI service without losing governance, memory, or project structure.

#### Add a service with a different SDK

Your existing project uses the OpenAI Agents SDK for `research-agent`. You need a new service that uses CrewAI:

```
$ covenant add-service content-writer --sdk crewai
```

```
  services/content_writer/
  +  __init__.py
  +  manager.py
  +  tools.py
  +  agents/__init__.py
  +  agents/example_agent.py
  +  schemas/__init__.py
  +  schemas/types.py
  +  memory/README.md

  +-------------------------------+
  |  Next Steps                   |
  |                               |
  |  Service 'content_writer'     |
  |  registered.                  |
  |                               |
  |  SDK: crewai                  |
  |                               |
  |  1. Edit services/            |
  |     content_writer/agents/    |
  |     example_agent.py          |
  |  2. Define types in services/ |
  |     content_writer/schemas/   |
  |     types.py                  |
  |  3. Wire agents in services/  |
  |     content_writer/manager.py |
  |  4. Run: covenant status      |
  |                               |
  |  The manager writes exit      |
  |  reports automatically.       |
  +-------------------------------+
```

**What's happening:** The scaffolded code uses CrewAI's patterns (Crew, Agent, Task) instead of the OpenAI Agents SDK's patterns. But the governance layer is identical: the same exit report format, the same `registry/agents.json` entry, the same memory directories, the same convention rules. The manager still writes exit reports automatically.

#### Both services coexist

```
$ covenant status
```

```
  +-------------------------------+
  |  Project Status               |
  |                               |
  |  my-project                   |
  |  Governance: active           |
  |  Services:   2                |
  |  Updated:    2026-08-14...    |
  +-------------------------------+

  Services
  +------------------+--------+--------+----------------------+
  | Name             | SDK    | Status | Last Run             |
  +------------------+--------+--------+----------------------+
  | research-agent   | openai | active | 2026-08-14T10:15:00Z |
  | content-writer   | crewai | active | never                |
  +------------------+--------+--------+----------------------+
```

**What's happening:** The status dashboard shows both services side by side. Different SDKs, same governance. Exit reports from the OpenAI service and the CrewAI service are stored in the same `memory/inheritance/` directory. `covenant remember` searches across both. `covenant consolidate` distills both into a unified summary.

#### Governance stays the same

The critical point: when you switch SDKs, you do not lose:
- Exit report history from prior services
- Memos between services
- Consolidated summaries
- Audit scores
- Convention rules for your IDE
- GOVERNANCE.md rules

The SDK is the execution layer. Governance is the structural layer. They are independent by design.

#### Search across SDK boundaries

```
$ covenant remember "API error handling"
```

Results include findings from both the OpenAI service and the CrewAI service. The governance layer does not know or care which SDK produced the finding. A lesson learned in one SDK applies to the other because the exit report format is universal.

**Where this leads:** You can add a LangGraph service next, or migrate an existing service from one SDK to another. The governance layer is the constant. The SDKs are interchangeable. This is the flexibility story: you are not locked into a framework. You are locked into governance. And that is the lock you want.

**Commands used:** `add-service`, `status`, `remember`

---

## Roadmap Phases

### Phase 1: Foundation (v0.1--v0.5) -- SHIPPED

The scaffolding and observation layer. Eight commands that create governed projects, track what agents do, and build institutional memory.

- Project scaffolding with SDK choice (OpenAI, CrewAI, LangGraph)
- Exit reports as the atomic unit of governance
- Memory inheritance: exit reports, memos, consolidated summaries
- Convention rules for Cursor and Claude Code
- 10-point structural audit
- Environment validation
- Branded terminal output (infinity symbol, gold/ink/oxblood palette)

Phase 1 proved the thesis: governance can be structural, not aspirational, and it can be SDK-agnostic.

---

### Phase 2: Runtime Integration (v0.6--v0.8)

Phase 1 scaffolds. Phase 2 makes governance active at runtime. The gap today: you scaffold a governed project, but you still run services yourself and hope exit reports get written. Phase 2 closes that gap.

#### `covenant run <service>`

Execute a service through the CLI with automatic exit report writing, usage capture, and error handling.

```
$ covenant run research-agent
```

```
  +-------------------------------+
  |  Running: research-agent      |
  |  SDK: openai                  |
  |  Started: 2026-10-01T14:00Z   |
  +-------------------------------+

  ... agent output ...

  +-------------------------------+
  |  Run Complete                 |
  |                               |
  |  Status:   completed          |
  |  Duration: 12.3s              |
  |  Tokens:   2,340              |
  |  Cost:     $0.02              |
  |                               |
  |  Exit report written to       |
  |  memory/inheritance/          |
  +-------------------------------+
```

No more "run it yourself and hope the exit report gets written." The CLI manages the full lifecycle: start, capture, report, store.

#### `covenant watch`

Live monitoring mode. Watch exit reports as they are written, surface failures in real-time, show token burn rate.

```
$ covenant watch
```

```
  Watching my-project...  (Ctrl+C to stop)

  14:00:03  research-agent   started
  14:00:15  research-agent   completed   12.3s   2,340 tokens
  14:01:00  summarizer       started
  14:01:45  summarizer       failed      45.1s   API timeout
            ^ Recommendation: Add configurable timeout (seen 2x before)
```

Think `tail -f` for governance. Failures surface with context from prior exit reports. Recurring failures are flagged automatically.

#### Baseline Tracking

First successful run sets a performance baseline: duration, tokens, success rate. Subsequent runs are compared against the baseline.

```
$ covenant status
```

```
  Services
  +------------------+----------+----------+-----------+
  | Name             | Baseline | Current  | Trend     |
  +------------------+----------+----------+-----------+
  | research-agent   | 9.8s     | 12.3s    | +25%      |
  | summarizer       | 3.2s     | 3.1s     | stable    |
  +------------------+----------+----------+-----------+

  ! research-agent duration increased 25% from baseline
```

Regression is detected early, before it becomes a production incident.

#### `covenant upgrade`

Install the full Covenant Framework (hooks, lifecycle management, Constitutional enforcement) into an existing covenant-cli project. The gateway from lightweight governance to full governance.

```
$ covenant upgrade
```

This is the bridge between covenant-cli (the scaffolding tool) and the Covenant Framework (the runtime governance engine). Projects that outgrow the CLI's governance layer can upgrade without starting over.

#### Auto-Consolidation

After a configurable number of runs (default: 10), the CLI automatically consolidates exit reports. Memory stays lean without manual intervention.

---

### Phase 3: Intelligence (v0.9--v1.0)

Phase 2 makes governance active. Phase 3 makes it intelligent. The system stops being a record-keeper and starts being an advisor.

#### `covenant suggest`

Based on exit report history, suggest specific improvements.

```
$ covenant suggest research-agent
```

```
  +-------------------------------+
  |  Suggestions for              |
  |  research-agent               |
  +-------------------------------+

  1. Add retry logic for rate-limited endpoints
     Basis: 3 exit reports mention rate limiting
     (2026-08-10, 2026-08-11, 2026-08-13)

  2. Cache fetched URLs between runs
     Basis: 2 exit reports recommend caching
     (2026-08-05, 2026-08-09)

  3. Increase result limit from 5 to 20
     Basis: First exit report recommendation,
     never addressed
```

Suggestions are grounded in evidence from the project's own history. Not generic advice. Specific recommendations that the project's agents have already made.

#### `covenant compare`

Compare two services, two time periods, or a service against its baseline.

```
$ covenant compare research-agent --period "last 7 days" vs "prior 7 days"
```

```
  +-------------------------------+
  |  Comparison                   |
  |  research-agent               |
  +-------------------------------+

  Metric        Prior 7d     Last 7d     Change
  Runs          8            12          +50%
  Success rate  62%          83%         +21%
  Avg duration  22.1s        13.4s       -39%
  Avg tokens    3,100        2,340       -24%

  What changed:
  - Retry logic added (2026-08-10)
  - Deduplication improved (2026-08-09)
```

Quantitative governance. You can see whether your changes are working.

#### Pattern Detection

Automatically detect recurring failures across services and surface them proactively in `covenant status`:

```
  Detected Patterns
  - "rate limit" appears in 3 services (research-agent, summarizer, content-writer)
    Recommendation: extract shared retry logic to project-level tools
```

#### Cross-Project Learning

Export and import governance learnings between projects.

```
$ covenant export-learnings --output learnings.json
$ cd ../other-project
$ covenant import-learnings ../my-project/learnings.json
```

A team that governs five projects can share patterns. What one project learns about rate limiting benefits all projects.

#### `covenant report`

Generate a governance health report for stakeholders.

```
$ covenant report --format markdown --period "last 7 days"
```

Produces a Markdown (or HTML) report: what agents did, what they learned, what they cost, where they failed. Weekly governance summaries for teams that need to report on AI agent operations.

---

### Phase 4: Ecosystem (v1.0+)

Phase 3 makes a single project intelligent. Phase 4 makes covenant-cli a platform.

#### Plugin System

Custom SDK adapters, custom audit checks, custom governance rules.

```
$ covenant plugin install covenant-plugin-autogen
$ covenant add-service my-autogen-service --sdk autogen
```

Any agent framework becomes governable with a plugin. The community extends the SDK adapter layer without forking the CLI.

#### Community Governance Rules

Share and discover .mdc rule sets.

```
$ covenant rules install security-focused
$ covenant rules install cost-optimized
```

Governance rules as a shared resource. "Install the security-focused governance rules" or "the cost-optimized rules for high-volume agent runs."

#### CI/CD Integration

`covenant audit` as a GitHub Action or pre-commit hook. Governance enforced in the pipeline.

```yaml
# .github/workflows/governance.yml
- name: Governance Check
  run: |
    pip install covenant-cli
    covenant audit --min-score 8 --fail-on-warn
```

A pull request that breaks governance does not merge.

#### Dashboard

Web UI for multi-project governance overview. Token spend, success rates, failure patterns across all projects. For teams managing multiple governed agent projects.

#### MCP Server

Expose covenant-cli as an MCP tool server. AI agents call governance tools to self-govern at runtime.

```
$ covenant serve --mcp
```

The governance layer becomes callable by agents themselves. An agent can check project memory, read prior exit reports, and write its own -- all through MCP tool calls. This is the endgame: governance that agents participate in, not just submit to.

---

## Design Principles

Seven principles that guide every roadmap decision.

**1. Governance is structural, not aspirational.**
Rules are embedded in code, not written in docs and hoped for. Exit reports are written by scaffolded managers, not by disciplined developers. Convention rules are loaded into the IDE, not pasted into README files.

**2. Convention rules are the delivery mechanism.**
AI coding assistants enforce governance at development time. The .mdc files in `.cursor/rules/` and `.claude/rules/` are not documentation. They are the governance layer's enforcement arm in the IDE.

**3. Exit reports are the atomic unit.**
Everything builds on agents writing down what they did, what worked, what failed, and what the next run should know. Memory, consolidation, search, suggestions, comparison, pattern detection -- all of it depends on exit reports existing.

**4. SDK-agnostic governance.**
The governance layer works regardless of which agent framework you choose. OpenAI Agents SDK, CrewAI, LangGraph -- the exit report format is the same, the memory structure is the same, the audit checks are the same. Switch SDKs without losing governance.

**5. Memory grows in wisdom, not volume.**
Consolidation ensures the system gets smarter, not just bigger. Raw exit reports are distilled into compiled summaries. Compiled summaries rank higher in search. Over time, the project's memory becomes a curated knowledge base, not a pile of logs.

**6. The CLI scaffolds and observes; the SDK executes.**
Clear separation of concerns. covenant-cli does not replace your agent framework. It wraps it in governance. The CLI creates the structure, tracks the outcomes, and surfaces the learnings. The SDK runs the agents.

**7. Progressive complexity.**
Start with `init` and `add-service`. Those two commands give you a governed project. Discover `remember`, `audit`, `consolidate` when you need them. Use `run`, `watch`, `suggest` when you are ready. The CLI never forces features on you -- you adopt governance at your own pace.

---

## Success Metrics

How we know covenant-cli is working.

| Metric | Target | How Measured |
|--------|--------|--------------|
| Time to first governed agent run | Under 2 minutes | `covenant init --sdk openai` through first `covenant status` showing an exit report |
| Exit report coverage | 100% for CLI-generated managers | Scaffolded managers write exit reports by default; audit checks for coverage |
| Governance adoption depth | >30% of projects use `remember` or `consolidate` | Indicates users are using governance, not just scaffolding |
| SDK adapter coverage | Top 5 agent frameworks supported | OpenAI, CrewAI, LangGraph shipped; AutoGen and custom plugins in Phase 4 |
| Audit score distribution | Median score 8/10 across governed projects | Structural health is the norm, not the exception |
| Community contributions | 10+ shared governance rule sets by v1.0 | Governance rules as a shared resource |

---

*The difference between an agent that works once and an agent you can trust is governance. covenant-cli makes governance structural, from the first line of code.*
