"""covenant audit -- structural health check for governed projects."""

import hashlib
import json
import re
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
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


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run_checks(project_root: Path) -> list[dict]:
    """Run all 10 structural health checks. Returns list of check results."""
    results = []

    # Load registry once for multiple checks
    registry_path = project_root / "registry" / "agents.json"
    registry = {}
    registry_valid = False
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry_valid = True
    except (json.JSONDecodeError, FileNotFoundError):
        pass

    # 1. GOVERNANCE.md exists
    governance_path = project_root / "GOVERNANCE.md"
    if governance_path.exists():
        results.append({
            "status": "pass",
            "message": "GOVERNANCE.md exists",
        })
    else:
        results.append({
            "status": "fail",
            "message": "GOVERNANCE.md is missing",
        })

    # 2. GOVERNANCE.md integrity
    if governance_path.exists():
        stored_hash = registry.get("governanceHash")
        if stored_hash:
            actual_hash = _sha256_file(governance_path)
            if actual_hash == stored_hash:
                results.append({
                    "status": "pass",
                    "message": "GOVERNANCE.md integrity verified (SHA-256 match)",
                })
            else:
                results.append({
                    "status": "warn",
                    "message": "GOVERNANCE.md has been modified since init",
                })
        else:
            results.append({
                "status": "warn",
                "message": "Cannot verify GOVERNANCE.md integrity -- no stored hash",
            })
    else:
        results.append({
            "status": "fail",
            "message": "Cannot verify GOVERNANCE.md integrity -- file missing",
        })

    # 3. Registry exists and valid JSON
    if registry_path.exists() and registry_valid:
        results.append({
            "status": "pass",
            "message": "Registry exists and contains valid JSON",
        })
    elif registry_path.exists():
        results.append({
            "status": "fail",
            "message": "Registry exists but contains invalid JSON",
        })
    else:
        results.append({
            "status": "fail",
            "message": "Registry file missing (registry/agents.json)",
        })

    # 4. Every registered service has a directory
    services = registry.get("services", [])
    if not services:
        results.append({
            "status": "warn",
            "message": "No services registered -- run: covenant add-service <name>",
        })
    else:
        all_dirs_exist = True
        missing = []
        for svc in services:
            slug = svc.get("slug", "")
            svc_dir = project_root / "services" / slug
            if not svc_dir.is_dir():
                all_dirs_exist = False
                missing.append(slug)
        if all_dirs_exist:
            results.append({
                "status": "pass",
                "message": f"All {len(services)} service directories exist",
            })
        else:
            results.append({
                "status": "fail",
                "message": f"Missing service directories: {', '.join(missing)}",
            })

    # 5. Every service has at least one exit report
    inheritance_dir = project_root / "memory" / "inheritance"
    if services:
        report_files = (
            list(inheritance_dir.glob("*.json")) if inheritance_dir.exists() else []
        )
        missing_reports = []
        for svc in services:
            slug = svc.get("slug", "")
            svc_reports = [f for f in report_files if slug in f.stem]
            if not svc_reports:
                missing_reports.append(slug)
        if not missing_reports:
            results.append({
                "status": "pass",
                "message": f"All services have exit reports",
            })
        else:
            results.append({
                "status": "warn",
                "message": f"{', '.join(missing_reports)} has 0 exit reports",
            })
    else:
        results.append({
            "status": "warn",
            "message": "No services to check for exit reports",
        })

    # 6. Agent files: each .py in agents/ has exactly one Agent( definition
    agents_issues = []
    for svc in services:
        slug = svc.get("slug", "")
        agents_dir = project_root / "services" / slug / "agents"
        if not agents_dir.is_dir():
            continue
        for py_file in agents_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                count = len(re.findall(r"Agent\(", content))
                if count != 1:
                    rel_path = f"{slug}/agents/{py_file.name}"
                    agents_issues.append(f"{rel_path} has {count} Agent() definitions")
            except OSError:
                continue

    if not agents_issues:
        results.append({
            "status": "pass",
            "message": "Agent files have correct Agent() definitions",
        })
    else:
        results.append({
            "status": "fail",
            "message": agents_issues[0],
        })

    # 7. Schema files contain class.*BaseModel
    schema_issues = []
    for svc in services:
        slug = svc.get("slug", "")
        schemas_dir = project_root / "services" / slug / "schemas"
        if not schemas_dir.is_dir():
            continue
        for py_file in schemas_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                if not re.search(r"class\s+\w+.*BaseModel", content):
                    rel_path = f"{slug}/schemas/{py_file.name}"
                    schema_issues.append(f"{rel_path} missing BaseModel class")
            except OSError:
                continue

    if not schema_issues:
        results.append({
            "status": "pass",
            "message": "Schema files contain BaseModel definitions",
        })
    else:
        results.append({
            "status": "warn",
            "message": schema_issues[0],
        })

    # 8. Manager has _write_exit_report method
    manager_issues = []
    for svc in services:
        slug = svc.get("slug", "")
        manager_path = project_root / "services" / slug / "manager.py"
        if not manager_path.exists():
            manager_issues.append(f"{slug}/manager.py not found")
            continue
        try:
            content = manager_path.read_text(encoding="utf-8")
            if "_write_exit_report" not in content:
                manager_issues.append(f"{slug}/manager.py missing _write_exit_report")
        except OSError:
            manager_issues.append(f"{slug}/manager.py unreadable")

    if not manager_issues:
        results.append({
            "status": "pass",
            "message": "Manager files have _write_exit_report method",
        })
    else:
        results.append({
            "status": "warn",
            "message": manager_issues[0],
        })

    # 9. IDE convention rules present
    has_cursor = (
        project_root / ".cursor" / "rules" / "governance.mdc"
    ).exists()
    has_claude = (
        project_root / ".claude" / "rules" / "governance.mdc"
    ).exists()
    if has_cursor or has_claude:
        results.append({
            "status": "pass",
            "message": "IDE convention rules present",
        })
    else:
        results.append({
            "status": "fail",
            "message": "No IDE convention rules found -- re-run covenant init",
        })

    # 10. Memory directories exist
    has_inheritance = (project_root / "memory" / "inheritance").is_dir()
    has_memos = (project_root / "memory" / "memos").is_dir()
    if has_inheritance and has_memos:
        results.append({
            "status": "pass",
            "message": "Memory directories exist (inheritance, memos)",
        })
    else:
        missing = []
        if not has_inheritance:
            missing.append("memory/inheritance/")
        if not has_memos:
            missing.append("memory/memos/")
        results.append({
            "status": "fail",
            "message": f"Missing memory directories: {', '.join(missing)}",
        })

    return results


@click.command()
def audit_command():
    """Run a 10-point structural health check.

    Verifies governance files, registry integrity, service structure,
    agent definitions, schema files, and memory directories.
    """
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    console.print()
    console.print(branded_panel(
        f"[{INK_LIGHT}]Running 10-point structural health check...[/]",
        title="Audit",
    ))
    console.print()

    results = _run_checks(project_root)

    # Display each check
    pass_count = 0
    warn_count = 0
    fail_count = 0
    score = 0

    for r in results:
        status = r["status"]
        message = r["message"]

        if status == "pass":
            pass_count += 1
            score += 10
            label = f"[{GREEN}][pass][/]"
        elif status == "warn":
            warn_count += 1
            score += 5
            label = f"[{GOLD}][warn][/]"
        else:
            fail_count += 1
            label = f"[{OXBLOOD}][fail][/]"

        console.print(f"  {label}  [{INK_LIGHT}]{message}[/]")

    # Summary
    console.print()

    if score >= 90:
        score_color = GREEN
    elif score >= 70:
        score_color = GOLD
    else:
        score_color = OXBLOOD

    console.print(
        f"  [{INK_LIGHT}]Health:[/] "
        f"[{GREEN}]{pass_count}[/] [{INK_LIGHT}]pass,[/] "
        f"[{GOLD}]{warn_count}[/] [{INK_LIGHT}]warn,[/] "
        f"[{OXBLOOD}]{fail_count}[/] [{INK_LIGHT}]fail[/]"
    )
    console.print(f"  [{INK_LIGHT}]Score:[/]  [{score_color}]{score}/100[/]")
    console.print()
