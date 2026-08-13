"""covenant status -- show project health."""

import json
from datetime import datetime
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
    branded_table,
    print_error,
    GOLD,
    INK_LIGHT,
    OXBLOOD,
    GREEN,
)


def _find_project_root() -> Path | None:
    """Walk up from cwd to find a directory with registry/agents.json."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "registry" / "agents.json").exists():
            return parent
    return None


def _load_registry(project_root: Path) -> dict:
    """Load the agent registry."""
    registry_path = project_root / "registry" / "agents.json"
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _find_exit_reports(project_root: Path, limit: int = 5) -> list[dict]:
    """Find recent exit reports from memory/inheritance/."""
    inheritance_dir = project_root / "memory" / "inheritance"
    if not inheritance_dir.exists():
        return []

    reports = []
    json_files = sorted(
        inheritance_dir.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for json_file in json_files[:limit]:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            reports.append({
                "file": json_file.name,
                "service": data.get("service", "unknown"),
                "status": data.get("status", "unknown"),
                "timestamp": data.get("timestamp", "unknown"),
                "duration": data.get("duration_seconds", "?"),
            })
        except (json.JSONDecodeError, KeyError):
            reports.append({
                "file": json_file.name,
                "service": "parse error",
                "status": "error",
                "timestamp": "?",
                "duration": "?",
            })

    return reports


def _check_warnings(project_root: Path, registry: dict) -> list[str]:
    """Check for common project health issues."""
    warnings = []

    if not (project_root / "GOVERNANCE.md").exists():
        warnings.append("GOVERNANCE.md is missing")

    if not (project_root / "memory" / "inheritance").exists():
        warnings.append("memory/inheritance/ directory is missing")

    if not (project_root / "memory" / "memos").exists():
        warnings.append("memory/memos/ directory is missing")

    if not registry.get("services"):
        warnings.append("No services registered -- run: covenant add-service <name>")

    # Check for services without exit reports
    inheritance_dir = project_root / "memory" / "inheritance"
    if inheritance_dir.exists():
        report_files = list(inheritance_dir.glob("*.json"))
        for service in registry.get("services", []):
            service_reports = [
                f for f in report_files
                if service["slug"] in f.stem
            ]
            if not service_reports and service.get("lastRun"):
                warnings.append(
                    f"Service '{service['slug']}' has run but has no exit reports"
                )

    has_cursor = (project_root / ".cursor" / "rules" / "governance.mdc").exists()
    has_claude = (project_root / ".claude" / "rules" / "governance.mdc").exists()
    if not has_cursor and not has_claude:
        warnings.append("No IDE convention rules found -- re-run covenant init")

    return warnings


@click.command()
def status_command():
    """Show project governance health."""
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    registry = _load_registry(project_root)

    # --- Header ---
    project_name = project_root.name
    governance_exists = (project_root / "GOVERNANCE.md").exists()
    governance_status = f"[{GREEN}]active[/]" if governance_exists else f"[{OXBLOOD}]missing[/]"

    console.print()
    console.print(
        branded_panel(
            f"[bold {GOLD}]{project_name}[/]\n"
            f"[{INK_LIGHT}]Governance:[/] {governance_status}\n"
            f"[{INK_LIGHT}]Services:[/]   {len(registry.get('services', []))}\n"
            f"[{INK_LIGHT}]Updated:[/]    {registry.get('lastUpdated', 'never')}",
            title="Project Status",
        )
    )

    # --- Services table ---
    services = registry.get("services", [])
    if services:
        table = branded_table(
            "Services",
            columns=[
                ("Name", f"bold {GOLD}"),
                ("Path", INK_LIGHT),
                ("Status", "bold"),
                ("Last Run", INK_LIGHT),
            ],
        )

        for svc in services:
            status_str = svc.get("status", "unknown")
            if status_str == "registered":
                status_display = f"[{GOLD}]registered[/]"
            elif status_str == "active":
                status_display = f"[{GREEN}]active[/]"
            else:
                status_display = f"[{INK_LIGHT}]{status_str}[/]"

            table.add_row(
                svc.get("name", "?"),
                svc.get("path", "?"),
                status_display,
                svc.get("lastRun", "never") or "never",
            )

        console.print()
        console.print(table)

    # --- Exit reports ---
    reports = _find_exit_reports(project_root)
    if reports:
        report_table = branded_table(
            "Recent Exit Reports",
            columns=[
                ("Service", f"bold {GOLD}"),
                ("Status", "bold"),
                ("Duration", INK_LIGHT),
                ("Timestamp", INK_LIGHT),
            ],
        )

        for r in reports:
            status_str = r["status"]
            if status_str == "completed":
                status_display = f"[{GREEN}]completed[/]"
            elif status_str == "failed":
                status_display = f"[{OXBLOOD}]failed[/]"
            else:
                status_display = f"[{GOLD}]{status_str}[/]"

            duration = f"{r['duration']}s" if r["duration"] != "?" else "?"
            report_table.add_row(r["service"], status_display, duration, r["timestamp"])

        console.print()
        console.print(report_table)
    else:
        console.print(f"\n[{INK_LIGHT}]No exit reports yet. Run a service to generate one.[/]")

    # --- Warnings ---
    warnings = _check_warnings(project_root, registry)
    if warnings:
        console.print()
        for w in warnings:
            console.print(f"  [{OXBLOOD}]![/] [{INK_LIGHT}]{w}[/]")

    console.print()
