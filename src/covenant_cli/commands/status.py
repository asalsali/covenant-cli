"""covenant status -- show project health."""

import json
from datetime import datetime, timezone
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


def _format_tokens(n: int) -> str:
    """Format a token count for display (e.g. 1234 -> '1.2K', 1234567 -> '1.2M')."""
    if n <= 0:
        return "--"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


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


def _load_all_exit_reports(project_root: Path) -> list[dict]:
    """Load all exit reports from memory/inheritance/, sorted newest first."""
    inheritance_dir = project_root / "memory" / "inheritance"
    if not inheritance_dir.exists():
        return []

    reports = []
    json_files = sorted(
        inheritance_dir.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for json_file in json_files:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            data["_filename"] = json_file.name
            reports.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return reports


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
            # Capture what_failed for details column
            what_failed = data.get("what_failed", [])
            first_failure = ""
            if what_failed and isinstance(what_failed, list) and what_failed:
                first_failure = str(what_failed[0])[:60]
            elif isinstance(what_failed, str) and what_failed:
                first_failure = what_failed[:60]

            reports.append({
                "file": json_file.name,
                "service": data.get("service", "unknown"),
                "status": data.get("status", "unknown"),
                "timestamp": data.get("timestamp", "unknown"),
                "duration": data.get("duration_seconds", "?"),
                "details": first_failure,
            })
        except (json.JSONDecodeError, KeyError):
            reports.append({
                "file": json_file.name,
                "service": "parse error",
                "status": "error",
                "timestamp": "?",
                "duration": "?",
                "details": "",
            })

    return reports


def _service_stats(all_reports: list[dict], slug: str) -> dict:
    """Compute run stats and latest info for a service from exit reports."""
    svc_reports = [
        r for r in all_reports
        if slug in r.get("_filename", "") or slug == r.get("service", "")
    ]
    total = len(svc_reports)
    completed = sum(1 for r in svc_reports if r.get("status") == "completed")

    # Find most recent timestamp
    last_run = None
    latest_recommendations = []
    for r in svc_reports:
        ts = r.get("timestamp")
        if ts and (last_run is None or ts > last_run):
            last_run = ts
            latest_recommendations = r.get("recommendations", [])

    # Aggregate usage stats across all reports for this service
    total_tokens = 0
    total_cost = 0.0
    has_usage = False
    for r in svc_reports:
        usage = r.get("usage")
        if usage and isinstance(usage, dict):
            has_usage = True
            total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            total_cost += usage.get("total_cost", 0.0)

    return {
        "total": total,
        "completed": completed,
        "last_run": last_run,
        "recommendations": latest_recommendations,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "has_usage": has_usage,
    }


def _compute_health(
    stats: dict,
    trust_data: dict | None,
    drift_warnings: list[str],
    slug: str,
) -> tuple[int, str]:
    """Compute composite health score for a service.

    Returns (score 0-100, label).
    """
    score = 50

    # Success rate contribution: 0-30 points
    total = stats.get("total", 0)
    completed = stats.get("completed", 0)
    success_rate = (completed / total) if total > 0 else 0.0
    score += int(success_rate * 30)

    # Trust bonus: trust level * 5 (0-15 points)
    if trust_data:
        trust_entry = trust_data.get(slug, {})
        score += trust_entry.get("level", 0) * 5

    # Recency bonus: 10 if within 7 days, 5 if within 30 days
    last_run = stats.get("last_run")
    if last_run:
        try:
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_ago = (now - last_dt).days
            if days_ago <= 7:
                score += 10
            elif days_ago <= 30:
                score += 5
        except (ValueError, TypeError):
            pass

    # Drift penalty: -20 per drift warning matching this slug
    for warning in drift_warnings:
        if warning.startswith(f"{slug}:"):
            score -= 20

    # Clamp 0-100
    score = max(0, min(100, score))

    # Label
    if score >= 80:
        label = "healthy"
    elif score >= 50:
        label = "fair"
    else:
        label = "degraded"

    return score, label


def _compute_drift_warnings(
    project_root: Path,
    all_reports: list[dict],
    services: list[dict],
) -> list[str]:
    """Quick inline drift check against baselines.json for health scoring."""
    baselines_path = project_root / "registry" / "baselines.json"
    if not baselines_path.exists():
        return []

    try:
        baselines = json.loads(baselines_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    warnings: list[str] = []
    for svc in services:
        slug = svc.get("slug", "")
        if slug not in baselines:
            continue
        bl = baselines[slug]

        svc_reports = [
            r for r in all_reports
            if slug in r.get("_filename", "") or slug == r.get("service", "")
        ]
        total = len(svc_reports)
        if total == 0:
            continue

        completed = sum(1 for r in svc_reports if r.get("status") == "completed")
        success_rate = completed / total

        # Token consumption
        total_tokens = 0
        for r in svc_reports:
            usage = r.get("usage")
            if usage and isinstance(usage, dict):
                total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        avg_tokens = total_tokens / total

        bl_tokens = bl.get("avgTokensPerRun", 0)
        bl_rate = bl.get("successRate", 0)

        if bl_tokens > 0 and avg_tokens > bl_tokens * 1.3:
            warnings.append(f"{slug}: token drift")
        if bl_rate > 0 and success_rate < bl_rate * 0.7:
            warnings.append(f"{slug}: success rate drift")

    return warnings


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
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON.")
def status_command(output_json):
    """Show project governance health."""
    project_root = _find_project_root()
    if project_root is None:
        if output_json:
            click.echo(json.dumps({"error": "Not inside a covenant project"}))
        else:
            print_error(
                "Not inside a covenant project. "
                "Run [bold]covenant init <name>[/bold] first."
            )
        raise SystemExit(1)

    registry = _load_registry(project_root)

    # --- Shared data needed by both JSON and Rich paths ---
    project_name = project_root.name
    governance_exists = (project_root / "GOVERNANCE.md").exists()

    # Count unread memos
    unread_memos = 0
    memos_dir = project_root / "memory" / "memos"
    if memos_dir.exists():
        for memo_file in memos_dir.glob("*.json"):
            try:
                memo_data = json.loads(memo_file.read_text(encoding="utf-8"))
                if not memo_data.get("read", False):
                    unread_memos += 1
            except (json.JSONDecodeError, OSError):
                continue

    # Find last consolidation date
    last_consolidated = "never"
    consolidated_files = sorted(
        (project_root / "memory").glob("consolidated-*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if consolidated_files:
        try:
            cdata = json.loads(
                consolidated_files[0].read_text(encoding="utf-8")
            )
            last_consolidated = cdata.get("consolidated_at", "unknown")[:10]
        except (json.JSONDecodeError, OSError):
            last_consolidated = consolidated_files[0].stem.replace("consolidated-", "")

    # --- Load all exit reports for stats ---
    all_reports = _load_all_exit_reports(project_root)

    # --- JSON output branch ---
    if output_json:
        services = registry.get("services", [])
        trust_path = project_root / "registry" / "trust.json"
        trust_data = {}
        if trust_path.exists():
            try:
                trust_data = json.loads(trust_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        drift_warnings = _compute_drift_warnings(project_root, all_reports, services)

        svc_list = []
        for svc in services:
            slug = svc.get("slug", "")
            stats = _service_stats(all_reports, slug)
            health_score, health_label = _compute_health(
                stats, trust_data, drift_warnings, slug,
            )
            svc_entry = {
                "name": svc.get("name", slug),
                "slug": slug,
                "status": svc.get("status", "unknown"),
                "runs": stats["total"],
                "completed": stats["completed"],
                "successRate": round(
                    (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1
                ),
                "totalTokens": stats["total_tokens"],
                "lastRun": stats["last_run"],
                "health": health_score,
                "healthLabel": health_label,
            }
            trust_entry = trust_data.get(slug)
            if trust_entry:
                svc_entry["trust"] = trust_entry.get("label", "Untested")
            svc_list.append(svc_entry)

        payload = {
            "project": project_name,
            "governance": "active" if governance_exists else "missing",
            "services": svc_list,
            "unreadMemos": unread_memos,
            "lastConsolidated": last_consolidated,
        }
        click.echo(json.dumps(payload))
        return

    # --- Rich output branch ---
    governance_status = f"[{GREEN}]active[/]" if governance_exists else f"[{OXBLOOD}]missing[/]"

    header_lines = [
        f"[bold {GOLD}]{project_name}[/]",
        f"[{INK_LIGHT}]Governance:[/] {governance_status}",
        f"[{INK_LIGHT}]Services:[/]   {len(registry.get('services', []))}",
        f"[{INK_LIGHT}]Updated:[/]    {registry.get('lastUpdated', 'never')}",
    ]
    if unread_memos > 0:
        header_lines.append(
            f"[{INK_LIGHT}]Unread memos:[/] [{OXBLOOD}]{unread_memos}[/]"
        )
    header_lines.append(
        f"[{INK_LIGHT}]Last consolidated:[/] {last_consolidated}"
    )

    console.print()
    console.print(
        branded_panel(
            "\n".join(header_lines),
            title="Project Status",
        )
    )

    # --- Services table ---
    services = registry.get("services", [])

    # Load trust data for trust column
    trust_path = project_root / "registry" / "trust.json"
    trust_data = {}
    if trust_path.exists():
        try:
            trust_data = json.loads(trust_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Compute drift warnings for health scoring
    drift_warnings = _compute_drift_warnings(project_root, all_reports, services)

    if services:
        table = branded_table(
            "Services",
            columns=[
                ("Name", f"bold {GOLD}"),
                ("Path", INK_LIGHT),
                ("Status", "bold"),
                ("Runs", INK_LIGHT),
                ("Tokens", INK_LIGHT),
                ("Trust", "bold"),
                ("Health", "bold"),
                ("Last Run", INK_LIGHT),
            ],
        )

        service_recommendations = {}

        for svc in services:
            slug = svc.get("slug", "")
            status_str = svc.get("status", "unknown")
            if status_str == "registered":
                status_display = f"[{GOLD}]registered[/]"
            elif status_str == "active":
                status_display = f"[{GREEN}]active[/]"
            else:
                status_display = f"[{INK_LIGHT}]{status_str}[/]"

            # Derive stats from exit reports
            stats = _service_stats(all_reports, slug)
            runs_display = (
                f"{stats['completed']}/{stats['total']}"
                if stats["total"] > 0
                else "0/0"
            )
            last_run_display = stats["last_run"] or "never"

            tokens_display = (
                _format_tokens(stats["total_tokens"])
                if stats["has_usage"]
                else "--"
            )

            if stats["recommendations"]:
                service_recommendations[svc.get("name", slug)] = stats["recommendations"]

            # Trust display
            trust_entry = trust_data.get(slug, {})
            trust_label = trust_entry.get("label", "Untested")
            trust_colors = {
                "Veteran": GREEN,
                "Trusted": "#5599ff",
                "Proven": GOLD,
                "Untested": INK_LIGHT,
            }
            trust_color = trust_colors.get(trust_label, INK_LIGHT)
            trust_display = f"[{trust_color}]{trust_label}[/]"

            # Health display
            health_score, health_label = _compute_health(
                stats, trust_data, drift_warnings, slug,
            )
            health_colors = {"healthy": GREEN, "fair": GOLD, "degraded": OXBLOOD}
            health_color = health_colors.get(health_label, INK_LIGHT)
            health_display = f"[{health_color}]{health_score} {health_label}[/]"

            table.add_row(
                svc.get("name", "?"),
                svc.get("path", "?"),
                status_display,
                runs_display,
                tokens_display,
                trust_display,
                health_display,
                last_run_display,
            )

        console.print()
        console.print(table)

        # Surface recommendations from recent exit reports
        if service_recommendations:
            console.print()
            for svc_name, recs in service_recommendations.items():
                for rec in recs[:2]:
                    console.print(
                        f"  [{GOLD}]>[/] [{INK_LIGHT}]{svc_name}:[/] {rec}"
                    )

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
                ("Details", INK_LIGHT),
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
            details = r.get("details", "")
            report_table.add_row(
                r["service"], status_display, duration, r["timestamp"], details
            )

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
