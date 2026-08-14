# covenant-cli

[![PyPI](https://img.shields.io/pypi/v/covenant-cli)](https://pypi.org/project/covenant-cli/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: Covenant Public License](https://img.shields.io/badge/license-Covenant%20Public-green)](LICENSE)

**Scaffold governed agent services.** Exit reports, typed I/O, memory inheritance -- from the first line of code.

## Why Covenant CLI?

Every AI agent framework gives you tools to *build* agents. None give you tools to *govern* them.

Covenant CLI scaffolds projects where governance is structural, not aspirational:

- **Exit reports** -- every service run writes what worked, what failed, and what the next run should know
- **Typed I/O** -- Pydantic models for every agent input and output, no `Dict[str, Any]`
- **Memory inheritance** -- agents read prior learnings before acting, not after failing
- **Registry tracking** -- every service and agent registered before it runs
- **Convention rules** -- IDE-native governance rules for Cursor and Claude Code

The difference between an agent that works once and an agent you can trust is governance.

## Quick Start

```bash
pip install covenant-cli

# Create a full governed app from a description (the fastest path)
covenant create "A research app that searches papers and writes reviews"

# Or scaffold manually:
covenant init my-project
cd my-project
covenant add-service research-agent
covenant status
```

## `covenant create` -- From Description to Governed App

The headline feature. Describe what you want, and Covenant builds a governed project with real agent code:

```bash
covenant create "A customer support bot that classifies tickets and drafts responses"
```

What happens:
1. Your description is sent to an LLM, which produces a structured plan
2. The plan is displayed for your review -- services, agents, typed I/O, pipeline
3. On confirmation, a complete Django webapp is scaffolded with:
   - Real agent definitions with specific instructions (not boilerplate)
   - Pydantic input/output models with typed fields from the plan
   - Manager orchestration with exit reports and inheritance
   - Tool stubs ready to implement
   - Full governance scaffold (registry, memory, IDE rules)

Every generated agent follows the same patterns as `covenant add-service` -- typed I/O, exit reports, memory inheritance. The difference is that the agents have real instructions and real types, not placeholders.

```bash
# Use a different template
covenant create "stock alert system" --template api

# Requires OPENAI_API_KEY
export OPENAI_API_KEY=sk-...
```

## Commands

| Command | Description |
|---------|-------------|
| `covenant create <description>` | Create a full governed app from a natural language description |
| `covenant init <name> [--template api\|webapp]` | Create a new governed project (default, FastAPI API, or Django webapp) |
| `covenant add-service <name>` | Add a governed service with manager, agents, typed schemas, and exit reports |
| `covenant status` | Show project health: services, recent exit reports, warnings |
| `covenant remember [query]` | Search exit reports, memos, and consolidated summaries by keyword |
| `covenant memo send/list/read` | Cross-service communication via structured memos |
| `covenant consolidate` | Distill exit reports into summaries, optionally archive |
| `covenant doctor` | Validate project environment: Python, SDK, API keys, registry, governance |

## User Journeys

Four documented paths through the tool:

- [First-Time Setup](USER-JOURNEYS.md#journey-1-first-time-setup) -- scaffold a governed project from scratch
- [Iterative Development](USER-JOURNEYS.md#journey-2-iterative-development) -- the learning loop across runs
- [Debugging a Failing Agent](USER-JOURNEYS.md#journey-3-debugging-a-failing-agent) -- trace failures through exit reports
- [Team Onboarding](USER-JOURNEYS.md#journey-4-team-onboarding) -- orient a new team member in minutes

## The Governance Delta

Without covenant-cli, your agents:
- Run without purpose documentation
- Pass untyped data between steps
- Fail silently and repeat mistakes
- Have no memory of prior runs

With covenant-cli, your agents:
- Declare their mandate before acting
- Use Pydantic models for all I/O
- Write exit reports on every run
- Read inheritance before starting
- Track token usage and cost per run
- Coordinate through structured memos

Same agent SDK. Same model. Different discipline.

## Project Structure

```
my-project/
├── GOVERNANCE.md              # 18 governance rules
├── setup.sh                   # Auto-setup: venv, deps, migrations
├── run_pipeline.py            # Standalone pipeline runner
├── registry/agents.json       # Service and agent registry
├── memory/
│   ├── inheritance/           # Exit reports from prior runs
│   └── memos/                 # Cross-service communication
├── .cursor/rules/             # Cursor IDE governance rules
├── .claude/rules/             # Claude Code governance rules
└── services/
    └── my-service/
        ├── manager.py         # Orchestrator with exit reports
        ├── agents/            # One agent per file
        ├── schemas/types.py   # Pydantic models
        └── tools.py           # Shared tools
```

## Application Templates

`covenant init` supports three project templates via the `--template` flag:

| Template | Command | What You Get |
|----------|---------|-------------|
| **default** | `covenant init my-project` | CLI project with `src/main.py`, governance scaffold, services directory |
| **api** | `covenant init my-api --template api` | FastAPI app with REST endpoints for governed agent services (`/services`, `/runs`, `/health`) |
| **webapp** | `covenant init my-webapp --template webapp` | Django webapp with dashboard and governance UI |

All templates include the same governance foundation: `GOVERNANCE.md`, `registry/agents.json`, `memory/` directories, and IDE convention rules. The template determines the application layer on top.

### API Template

The API template generates a working FastAPI application:

```
my-api/
├── main.py                # FastAPI entry point
├── requirements.txt       # Python dependencies
├── runner.py              # Background task runner
├── routers/
│   ├── services.py        # Service CRUD + trigger endpoints
│   ├── runs.py            # Run detail + exit report endpoints
│   └── health.py          # Governance health check
├── models/
│   ├── schemas.py         # Pydantic request/response models
│   └── database.py        # File-based storage (reads same files as CLI)
├── GOVERNANCE.md
├── registry/agents.json
└── memory/
```

No database required -- the API reads the same governance files the CLI does.

## What's New in v0.8.0

- **`setup.sh` auto-generation** -- `covenant create` now generates a `setup.sh` script inside your project that automates post-generation setup: virtual environment creation, dependency installation, API key check, and Django migrations. Works on Linux, Mac, and Git Bash on Windows.
- **`run_pipeline.py` auto-generation** -- `covenant create` now generates a standalone pipeline runner that executes your full agent pipeline without Django. Run `python run_pipeline.py "your input"` to test agents immediately, or `--dry-run` to inspect the pipeline structure.

### v0.7.0

- **`covenant create`** -- describe what you want in natural language, get a full governed app with real agent code, typed I/O, and pipeline orchestration. The headline feature.
- Requires `OPENAI_API_KEY` (uses gpt-4o-mini for plan generation)

### v0.6.0

- **Application templates** -- `covenant init --template api` scaffolds a FastAPI governed agent API; `--template webapp` scaffolds a Django webapp
- **Three templates** -- default (CLI), api (FastAPI), webapp (Django) -- all sharing the same governance foundation

### v0.5.0

- **`covenant doctor`** -- validate project environment health: Python version, SDK, API keys, registry integrity, governance, memory directories, IDE rules, and service scaffolding

### v0.4.0

- **Usage tracking** -- token consumption and cost per service run, visible in `covenant status`
- **`covenant memo`** -- cross-service communication via structured memos (send/list/read)
- **`covenant consolidate`** -- distill exit reports into summaries with optional archiving
- **`covenant remember`** -- now searches memos and consolidated summaries (compiled-truth boost)
- **Status dashboard** -- unread memo count, last consolidation date, token totals per service
- **3 new governance rules** -- track usage, communicate via memos, consolidate regularly

## Roadmap

covenant-cli is heading toward runtime governance and intelligence. See [ROADMAP.md](ROADMAP.md) for the full plan.

**Coming next:**
- `covenant run <service>` -- execute services with automatic exit reports and usage capture
- `covenant watch` -- live monitoring with failure context from prior runs
- Baseline tracking -- detect regression before it becomes a production incident
- `covenant suggest` -- evidence-based improvement recommendations from your project's own history
- Plugin system -- make any agent framework governable

Six detailed user journeys and the full phase-by-phase plan are in the roadmap.

## Credits

Inspired by [mutta](https://github.com/maestromaximo/agent-sdk-mutta) by Alejandro Garcia Polo.

## License

[Covenant Public License v1.0](LICENSE) -- free for individuals and teams under $1M revenue. Contact the author for commercial licensing.
