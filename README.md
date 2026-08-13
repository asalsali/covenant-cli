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

# Create a governed project
covenant init my-project
cd my-project

# Add a governed service
covenant add-service research-agent

# Check project health
covenant status
```

## Commands

| Command | Description |
|---------|-------------|
| `covenant init <name>` | Create a new governed project with GOVERNANCE.md, registry, memory, and convention rules |
| `covenant add-service <name>` | Add a governed service with manager, agents, typed schemas, and exit reports |
| `covenant status` | Show project health: services, recent exit reports, warnings |
| `covenant remember [query]` | Search exit reports by keyword, with `--failed`, `--service`, `--limit` filters |

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

Same agent SDK. Same model. Different discipline.

## Project Structure

```
my-project/
├── GOVERNANCE.md              # 15 governance rules
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

## What's New in v0.3.0

- **`covenant remember`** -- search exit reports by keyword, filter by status or service
- **User Journeys** -- four guided paths from first install to team onboarding
- **Richer status output** -- exit report details in the dashboard

## Credits

Inspired by [mutta](https://github.com/maestromaximo/agent-sdk-mutta) by Alejandro Garcia Polo.

## License

[Covenant Public License v1.0](LICENSE) -- free for individuals and teams under $1M revenue. Contact the author for commercial licensing.
