"""covenant doctor -- validate project environment health."""

import json
import sys
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
    print_error,
    GOLD,
    GOLD_DIM,
    INK_LIGHT,
    OXBLOOD,
    GREEN,
)


# ── SDK metadata ─────────────────────────────────────────────────────

SDK_PACKAGES = {
    "openai": {"import": "agents", "pip": "openai-agents", "label": "openai-agents"},
    "crewai": {"import": "crewai", "pip": "crewai", "label": "crewai"},
    "langgraph": {"import": "langgraph", "pip": "langgraph", "label": "langgraph"},
}

SDK_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "crewai": "OPENAI_API_KEY",
    "langgraph": "OPENAI_API_KEY",
}


# ── Helpers ──────────────────────────────────────────────────────────

def _find_project_root() -> Path | None:
    """Walk up from cwd to find a directory with registry/agents.json."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "registry" / "agents.json").exists():
            return parent
    return None


def _tag(status: str) -> str:
    """Return a Rich-formatted status tag."""
    if status == "pass":
        return f"[{GREEN}][pass][/]"
    if status == "warn":
        return f"[{GOLD}][warn][/]"
    return f"[{OXBLOOD}][fail][/]"


# ── Individual checks ────────────────────────────────────────────────

def _check_python() -> tuple[str, str]:
    """Check Python version >= 3.10."""
    v = sys.version_info
    version_str = f"Python {v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 10):
        return "pass", version_str
    return "fail", f"Python {v.major}.{v.minor} found, 3.10+ required"


def _check_project_structure(project_root: Path | None) -> tuple[str, str]:
    """Check registry/agents.json exists."""
    if project_root is not None:
        return "pass", "registry/agents.json found"
    return "fail", "registry/agents.json not found -- not a covenant project"


def _check_sdk(registry: dict) -> tuple[str, str]:
    """Check the default SDK package is importable."""
    sdk = registry.get("defaultSdk", "")
    if not sdk:
        return "warn", "No defaultSdk set in registry"

    meta = SDK_PACKAGES.get(sdk)
    if meta is None:
        return "warn", f"Unknown SDK '{sdk}'"

    try:
        __import__(meta["import"])
        return "pass", f"{meta['label']} installed"
    except ImportError:
        return "warn", f"{meta['label']} not installed -- run: pip install {meta['pip']}"


def _check_api_key(registry: dict) -> tuple[str, str]:
    """Check the environment variable for the configured SDK."""
    import os

    sdk = registry.get("defaultSdk", "")
    env_var = SDK_API_KEYS.get(sdk)
    if env_var is None:
        return "warn", "Cannot determine required API key (no SDK set)"

    if os.environ.get(env_var):
        return "pass", f"{env_var} set"
    return "warn", f"{env_var} not set -- export it or add to .env"


def _check_registry_integrity(project_root: Path) -> tuple[str, str, dict | None]:
    """Validate registry/agents.json is valid JSON. Returns (status, msg, data)."""
    registry_path = project_root / "registry" / "agents.json"
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        services = data.get("services", [])
        return "pass", f"Registry valid ({len(services)} service{'s' if len(services) != 1 else ''})", data
    except json.JSONDecodeError as exc:
        return "fail", f"registry/agents.json is invalid JSON: {exc}", None


def _check_governance(project_root: Path) -> tuple[str, str]:
    """Check GOVERNANCE.md exists."""
    if (project_root / "GOVERNANCE.md").exists():
        return "pass", "GOVERNANCE.md present"
    return "fail", "GOVERNANCE.md missing"


def _check_memory_dirs(project_root: Path) -> tuple[str, str]:
    """Check memory/inheritance/ and memory/memos/ exist."""
    inheritance = (project_root / "memory" / "inheritance").is_dir()
    memos = (project_root / "memory" / "memos").is_dir()
    if inheritance and memos:
        return "pass", "Memory directories exist"
    missing = []
    if not inheritance:
        missing.append("memory/inheritance/")
    if not memos:
        missing.append("memory/memos/")
    return "fail", f"Missing: {', '.join(missing)}"


def _check_ide_rules(project_root: Path) -> tuple[str, str]:
    """Check .cursor/rules/ or .claude/rules/ has governance.mdc."""
    has_cursor = (project_root / ".cursor" / "rules" / "governance.mdc").exists()
    has_claude = (project_root / ".claude" / "rules" / "governance.mdc").exists()
    if has_cursor or has_claude:
        return "pass", "IDE rules present"
    return "warn", "No governance.mdc found -- re-run covenant init"


def _check_services(project_root: Path, registry: dict) -> list[tuple[str, str]]:
    """Check each registered service has a manager.py."""
    results = []
    for svc in registry.get("services", []):
        slug = svc.get("slug", svc.get("name", "unknown"))
        manager_path = project_root / "services" / slug / "manager.py"
        if manager_path.exists():
            results.append(("pass", f"{slug}/ manager.py exists"))
        else:
            results.append(("warn", f"{slug}/ manager.py missing"))
    return results


# ── Main command ─────────────────────────────────────────────────────

@click.command()
def doctor_command():
    """Check project environment health."""
    results: list[tuple[str, str]] = []

    # 1. Python version
    results.append(_check_python())

    # 2. Project structure (fail fast)
    project_root = _find_project_root()
    status, msg = _check_project_structure(project_root)
    results.append((status, msg))

    if project_root is None:
        _render(results)
        raise SystemExit(1)

    # 5. Registry integrity (run early so we can use the data)
    reg_status, reg_msg, registry = _check_registry_integrity(project_root)
    if registry is None:
        registry = {}

    # 3. SDK detection
    results.append(_check_sdk(registry))

    # 4. API key
    results.append(_check_api_key(registry))

    # 5. Registry integrity
    results.append((reg_status, reg_msg))

    # 6. GOVERNANCE.md
    results.append(_check_governance(project_root))

    # 7. Memory directories
    results.append(_check_memory_dirs(project_root))

    # 8. IDE rules
    results.append(_check_ide_rules(project_root))

    # 9. Services
    for svc_result in _check_services(project_root, registry):
        results.append(svc_result)

    _render(results)


def _render(results: list[tuple[str, str]]) -> None:
    """Render check results as a branded panel."""
    passes = sum(1 for s, _ in results if s == "pass")
    warns = sum(1 for s, _ in results if s == "warn")
    fails = sum(1 for s, _ in results if s == "fail")

    lines = []
    for status, msg in results:
        lines.append(f"  {_tag(status)} [{INK_LIGHT}]{msg}[/]")

    lines.append("")

    # Summary line
    summary = f"  {passes} pass, {warns} warn, {fails} fail"
    lines.append(f"[{INK_LIGHT}]{summary}[/]")

    # Final message
    if fails > 0:
        lines.append(f"  [{OXBLOOD}]Fix the failures above before running agents.[/]")
    elif warns > 0:
        lines.append(f"  [{GOLD}]Your project is ready with warnings.[/]")
    else:
        lines.append(f"  [{GREEN}]Your project is ready.[/]")

    console.print()
    console.print(
        branded_panel("\n".join(lines), title="Environment Check")
    )
    console.print()
