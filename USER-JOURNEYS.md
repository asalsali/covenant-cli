# User Journeys

Four paths through covenant-cli -- from first install to team-wide governance.

---

## Journey 1: First-Time Setup

**You are:** A developer who just heard about governed agents.
**You want:** A project scaffold with governance baked in.

### Install the CLI

```
pip install covenant-cli
```

### Create your first governed project

```
$ covenant init my-agent-project
```

The CLI prints the branded banner and a file tree showing everything it created:

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

  my-agent-project/
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
  |    cd my-agent-project        |
  |    pip install -e .           |
  |    covenant add-service       |
  |        my-first-agent         |
  |    covenant status            |
  |                               |
  |  Read GOVERNANCE.md           |
  |    -- it's the law.           |
  +-------------------------------+
```

**What just happened:** You have a project directory with governance built into the structure. `GOVERNANCE.md` contains 15 rules your agents will follow. `registry/agents.json` tracks every service. `memory/inheritance/` is where exit reports accumulate. Convention rules for Cursor and Claude Code are already in place.

### Add your first service

```
$ cd my-agent-project
$ covenant add-service research-agent
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

**What just happened:** The CLI scaffolded a complete service with a manager (orchestrator), an example agent, Pydantic schemas, a tools file, and a local memory directory. The service is registered in `registry/agents.json`. The manager is wired to write exit reports on every run.

### Check project health

```
$ covenant status
```

```
  +-------------------------------+
  |  Project Status               |
  |                               |
  |  my-agent-project             |
  |  Governance: active           |
  |  Services:   1                |
  |  Updated:    2026-08-13...    |
  +-------------------------------+

  Services
  +------------------+------+------------+----------+
  | Name             | Path | Status     | Last Run |
  +------------------+------+------------+----------+
  | research-agent   | ...  | registered | never    |
  +------------------+------+------------+----------+

  No exit reports yet. Run a service to generate one.
```

**What just happened:** The status command reads your registry, scans for exit reports, and checks for common health issues. Right now there are no exit reports because you haven't run the service yet. That changes after your first run.

### What's next

1. Open `services/research_agent/agents/example_agent.py` and replace the placeholder with your agent logic
2. Define your input/output types in `schemas/types.py`
3. Wire the agent into `manager.py`
4. Run your service -- the manager writes an exit report to `memory/inheritance/`
5. Run `covenant status` again to see the report appear

---

## Journey 2: Iterative Development

**You are:** A developer with a working service, running it repeatedly.
**You want:** To see what's improving, what keeps failing, what patterns emerge.

### Run your service a few times

After several runs of your research agent, exit reports accumulate in `memory/inheritance/`. Each one records what worked, what failed, and recommendations for the next run.

### Check what the system remembers

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

**What just happened:** The `remember` command reads every exit report in `memory/inheritance/` and displays them newest-first. You can see the pattern: the service improved over four runs. The timeout failure on Aug 12 led to a recommendation. The next successful run handled pagination correctly. This is the learning loop -- each run informs the next.

### Search for specific patterns

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

### Filter to failures only

```
$ covenant remember --failed
```

This shows only reports with `status: "failed"`. When you're debugging, you don't want to scroll past successes.

### Filter by service

```
$ covenant remember --service research_agent --limit 3
```

When your project has multiple services, this narrows the view to the one you care about.

### Check overall health

```
$ covenant status
```

```
  +-------------------------------+
  |  Project Status               |
  |                               |
  |  my-agent-project             |
  |  Governance: active           |
  |  Services:   2                |
  |  Updated:    2026-08-13...    |
  +-------------------------------+

  Services
  +------------------+------+--------+----------------------+
  | Name             | Path | Status | Last Run             |
  +------------------+------+--------+----------------------+
  | research-agent   | ...  | active | 2026-08-13T14:30:00Z |
  | summarizer       | ...  | active | 2026-08-13T13:00:00Z |
  +------------------+------+--------+----------------------+

  Recent Exit Reports
  +------------------+-----------+----------+----------------------+
  | Service          | Status    | Duration | Timestamp            |
  +------------------+-----------+----------+----------------------+
  | research-agent   | completed | 12.3s    | 2026-08-13T14:30:00Z |
  | summarizer       | completed | 3.2s     | 2026-08-13T13:00:00Z |
  | research-agent   | completed | 18.7s    | 2026-08-13T11:15:00Z |
  +------------------+-----------+----------+----------------------+
```

**What just happened:** The status dashboard gives you the full picture -- all services, their last run times, and the most recent exit reports across the project. You can see at a glance whether things are healthy or degrading.

### What's next

- When you see the same failure appearing across multiple reports, fix the underlying issue and watch it disappear from subsequent runs
- When recommendations repeat ("add retry logic", "add retry logic"), that's the system telling you what to build next
- Use `covenant remember` before making changes -- read what the system already knows before re-discovering it

---

## Journey 3: Debugging a Failing Agent

**You are:** A developer whose service just failed.
**You want:** To understand why, whether it's happened before, and what to do.

### The failure happens

Your summarizer service fails mid-run. The manager writes a partial exit report before exiting.

### Check what happened

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

**What just happened:** Two things are immediately clear. First, this is the same failure -- rate limiting on the OpenAI API. Second, the recommendation from the first failure ("implement rate limit handling") was never acted on. The system told you what to do four days ago.

### Search across all services for the pattern

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

**What just happened:** The cross-service search reveals that your research agent already solved this problem. It has retry logic with backoff, and its exit report even recommended extracting it into `tools.py` for shared use. The fix already exists in your codebase -- you just need to share it.

### Check project-wide health

```
$ covenant status
```

Look at the warnings section:

```
  ! Service 'summarizer' has run but produced failures
```

### The debugging flow

1. `covenant remember --failed` -- what failed recently?
2. `covenant remember "<error keyword>"` -- has this happened before?
3. Read the recommendations from prior reports -- has the system already told you how to fix this?
4. Check other services -- has a sibling service already solved this?
5. Fix the issue, run again, watch the next exit report confirm the fix

### What's next

- Extract the research agent's retry logic into the shared `tools.py`
- Import it in the summarizer's manager
- Run the summarizer again and verify the exit report shows `completed`
- The next `covenant remember "rate limit"` should show the fix working

---

## Journey 4: Team Onboarding

**You are:** A new team member who just cloned a governed project.
**You want:** To understand the structure and know where to start.

### Clone and orient

```
$ git clone git@github.com:team/our-agent-project.git
$ cd our-agent-project
```

### Check what exists

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
```

**What just happened:** Without reading any documentation, you already know the project has three services, all actively running, all recently successful. This is the project's vital signs at a glance.

### Read the governance rules

```
$ cat GOVERNANCE.md
```

This is the project's law -- 15 rules that every service follows. Read it before writing code. The rules cover exit reports, typed I/O, memory inheritance, and how services communicate.

### Understand what's been learned

```
$ covenant remember
```

```
  +-------------------------------+
  |  Exit Reports                 |
  |                               |
  |  Showing 10 of 47 reports     |
  +-------------------------------+

  research-agent  2026-08-12T14:30:00Z  completed  12.3s
    Worked:  API pagination handled correctly
    Failed:  --
    Recommends:  Add retry logic for rate-limited endpoints

  summarizer  2026-08-12T13:00:00Z  completed  3.2s
    Worked:  Chunked summarization with 2k token windows
    Failed:  --
    Recommends:  Test with longer inputs (>50k tokens)

  ...
```

47 exit reports. This project has history. Before you write new code or modify a service, search for what the system already knows about your area.

### Search before you build

Suppose you're tasked with adding caching to the research agent.

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

**What just happened:** Two prior runs already identified the need for caching and gave specific recommendations. You're not starting from scratch -- you're building on what the system has already learned.

### Understand the project structure

```
our-agent-project/
+-- GOVERNANCE.md              # The rules. Read this first.
+-- registry/agents.json       # Every service, registered and tracked
+-- memory/
|   +-- inheritance/           # Exit reports from every run
|   +-- memos/                 # Cross-service messages
+-- services/
|   +-- research_agent/        # Each service is self-contained
|   |   +-- manager.py         # Orchestrator, writes exit reports
|   |   +-- agents/            # One agent per file
|   |   +-- schemas/types.py   # Pydantic models for all I/O
|   |   +-- tools.py           # Shared utilities
|   |   +-- memory/            # Service-local learnings
|   +-- summarizer/
|   +-- report_writer/
+-- .cursor/rules/             # IDE governance rules (Cursor)
+-- .claude/rules/             # IDE governance rules (Claude Code)
```

### The onboarding flow

1. `covenant status` -- what services exist, are they healthy?
2. Read `GOVERNANCE.md` -- what are the rules?
3. `covenant remember` -- what has the system learned?
4. `covenant remember "<your task keyword>"` -- what does the system already know about what you're building?
5. Read the service you'll be working on: `manager.py` first, then `agents/`, then `schemas/`

### What's next

- Read the exit reports for the service you'll be modifying
- Check for open recommendations that align with your task
- Follow the patterns in `manager.py` -- it handles exit reports, memory reading, and registry updates
- Your IDE already has governance rules loaded (check `.cursor/rules/` or `.claude/rules/`)
