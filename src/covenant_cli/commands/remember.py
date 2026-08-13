"""covenant remember [query] -- search exit reports by keyword."""

import json
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


def _load_exit_reports(project_root: Path) -> list[dict]:
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


def _load_memos(project_root: Path) -> list[dict]:
    """Load all memo JSON files from memory/memos/, sorted newest first."""
    memos_dir = project_root / "memory" / "memos"
    if not memos_dir.exists():
        return []

    memos = []
    for memo_file in sorted(
        memos_dir.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    ):
        try:
            data = json.loads(memo_file.read_text(encoding="utf-8"))
            data["_filename"] = memo_file.name
            memos.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return memos


def _load_consolidated(project_root: Path) -> list[dict]:
    """Load all consolidated summary files, sorted newest first."""
    memory_dir = project_root / "memory"
    if not memory_dir.exists():
        return []

    summaries = []
    for cfile in sorted(
        memory_dir.glob("consolidated-*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    ):
        try:
            data = json.loads(cfile.read_text(encoding="utf-8"))
            data["_filename"] = cfile.name
            summaries.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return summaries


def _memo_matches_query(memo: dict, query: str) -> bool:
    """Check if a memo matches the query (case-insensitive substring)."""
    query_lower = query.lower()
    for field in ("from", "to", "message"):
        value = memo.get(field, "")
        if isinstance(value, str) and query_lower in value.lower():
            return True
    return False


def _consolidated_matches(summary: dict, query: str) -> list[dict]:
    """Find matching entries inside a consolidated summary.

    Returns a list of match dicts with service, text, and match_type.
    """
    query_lower = query.lower()
    matches = []

    for svc_name, svc_data in summary.get("services", {}).items():
        if not isinstance(svc_data, dict):
            continue

        # Search recurring_failures
        for failure in svc_data.get("recurring_failures", []):
            text = failure if isinstance(failure, str) else str(failure)
            if query_lower in text.lower():
                count = ""
                if isinstance(failure, dict):
                    count = f", {failure.get('count', '?')} occurrences"
                    text = failure.get("pattern", str(failure))
                matches.append({
                    "service": svc_name,
                    "text": text,
                    "match_type": f"recurring failure{count}",
                })

        # Search top_recommendations
        for rec in svc_data.get("top_recommendations", []):
            text = rec if isinstance(rec, str) else str(rec)
            if query_lower in text.lower():
                matches.append({
                    "service": svc_name,
                    "text": text,
                    "match_type": "recommendation",
                })

    return matches


def _matches_query(report: dict, query: str) -> bool:
    """Check if a report matches the query (case-insensitive substring)."""
    query_lower = query.lower()

    # Search in service name
    if query_lower in report.get("service", "").lower():
        return True

    # Search in status
    if query_lower in report.get("status", "").lower():
        return True

    # Search in what_worked list
    for item in report.get("what_worked", []):
        if isinstance(item, str) and query_lower in item.lower():
            return True

    # Search in what_failed list
    for item in report.get("what_failed", []):
        if isinstance(item, str) and query_lower in item.lower():
            return True

    # Search in recommendations list
    for item in report.get("recommendations", []):
        if isinstance(item, str) and query_lower in item.lower():
            return True

    return False


def _format_duration(seconds) -> str:
    """Format duration in seconds to a human-readable string."""
    if seconds is None or seconds == "?":
        return "?"
    try:
        s = float(seconds)
        if s < 60:
            return f"{s:.1f}s"
        minutes = int(s // 60)
        remaining = s % 60
        return f"{minutes}m {remaining:.0f}s"
    except (ValueError, TypeError):
        return str(seconds)


def _display_report(report: dict) -> None:
    """Display a single exit report in compact format."""
    service = report.get("service", "unknown")
    timestamp = report.get("timestamp", "unknown")
    status = report.get("status", "unknown")
    duration = _format_duration(report.get("duration_seconds"))

    # Status coloring
    if status == "completed":
        status_display = f"[{GREEN}]{status}[/]"
    elif status == "failed":
        status_display = f"[{OXBLOOD}]{status}[/]"
    else:
        status_display = f"[{GOLD}]{status}[/]"

    console.print(
        f"  [bold {GOLD}]{service}[/]  [{INK_LIGHT}]{timestamp}[/]  "
        f"{status_display}  [{INK_LIGHT}]{duration}[/]"
    )

    # What worked
    worked = report.get("what_worked", [])
    if worked:
        first = worked[0] if isinstance(worked, list) else str(worked)
        console.print(f"    [{GREEN}]Worked:[/] [{INK_LIGHT}]{first}[/]")
    else:
        console.print(f"    [{GREEN}]Worked:[/] [{INK_LIGHT}]--[/]")

    # What failed
    failed = report.get("what_failed", [])
    if failed:
        first = failed[0] if isinstance(failed, list) else str(failed)
        console.print(f"    [{OXBLOOD}]Failed:[/] [{INK_LIGHT}]{first}[/]")
    else:
        console.print(f"    [{OXBLOOD}]Failed:[/] [{INK_LIGHT}]--[/]")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        first = recs[0] if isinstance(recs, list) else str(recs)
        console.print(f"    [{GOLD}]Recommends:[/] [{INK_LIGHT}]{first}[/]")
    else:
        console.print(f"    [{GOLD}]Recommends:[/] [{INK_LIGHT}]--[/]")


@click.command()
@click.argument("query", required=False, default=None)
@click.option("--failed", is_flag=True, help="Show only failed reports.")
@click.option("--service", default=None, help="Filter to a specific service.")
@click.option("--limit", default=10, type=int, help="Max reports to show.")
def remember_command(query, failed, service, limit):
    """Search exit reports by keyword.

    QUERY is an optional search term. Without it, shows the most recent reports.
    """
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    reports = _load_exit_reports(project_root)
    memos = _load_memos(project_root)
    consolidated = _load_consolidated(project_root)

    has_any_data = reports or memos or consolidated

    if not has_any_data:
        console.print(f"\n[{INK_LIGHT}]No exit reports, memos, or consolidated summaries found.[/]")
        console.print(
            f"[{INK_LIGHT}]Run a service to generate data, "
            f"or check memory/inheritance/.[/]"
        )
        return

    # --- Consolidated matches (compiled-truth boost -- displayed FIRST) ---
    if query and consolidated:
        all_consolidated_matches = []
        for summary in consolidated:
            matches = _consolidated_matches(summary, query)
            all_consolidated_matches.extend(matches)

        if all_consolidated_matches:
            console.print()
            console.print(
                f"  [bold {GOLD}]Consolidated findings matching '{query}':[/]"
            )
            for m in all_consolidated_matches:
                console.print(
                    f"    [{GREEN}][compiled][/] [{GOLD}]{m['service']}:[/] "
                    f"[{INK_LIGHT}]\"{m['text']}\" ({m['match_type']})[/]"
                )
            console.print()

    # --- Exit reports ---
    filtered = reports

    if failed:
        filtered = [r for r in filtered if r.get("status") == "failed"]

    if service:
        filtered = [
            r for r in filtered
            if service.lower() in r.get("service", "").lower()
        ]

    if query:
        filtered = [r for r in filtered if _matches_query(r, query)]

    if filtered:
        total = len(filtered)
        showing = filtered[:limit]

        title = "Exit Reports"
        if query:
            title += f" matching '{query}'"
        console.print()
        console.print(branded_panel(
            f"[{INK_LIGHT}]Showing {len(showing)} of {total} reports[/]",
            title=title,
        ))
        console.print()

        for report in showing:
            _display_report(report)
            console.print()

        if total > limit:
            remaining = total - limit
            console.print(
                f"  [{INK_LIGHT}]... and {remaining} more. "
                f"Use --service to narrow or --limit to show more.[/]"
            )

    # --- Memo matches ---
    if query and memos:
        matching_memos = [m for m in memos if _memo_matches_query(m, query)]
        if matching_memos:
            console.print()
            console.print(
                f"  [bold {GOLD}]Memos matching '{query}':[/]"
            )
            for m in matching_memos:
                sender = m.get("from", "?")
                recipient = m.get("to", "?")
                timestamp = m.get("timestamp", "?")
                message = m.get("message", "")
                truncated = message[:80] + "..." if len(message) > 80 else message
                console.print(
                    f"    [{GOLD}]{sender}[/] [{INK_LIGHT}]->[/] "
                    f"[{GOLD}]{recipient}[/]  [{INK_LIGHT}]{timestamp}[/]"
                )
                console.print(
                    f"      [{INK_LIGHT}]\"{truncated}\"[/]"
                )
            console.print()

    # Check if nothing matched at all
    if query:
        has_report_matches = bool(filtered)
        has_memo_matches = bool(memos and [m for m in memos if _memo_matches_query(m, query)])
        has_consolidated_matches = bool(consolidated and any(
            _consolidated_matches(s, query) for s in consolidated
        ))
        if not has_report_matches and not has_memo_matches and not has_consolidated_matches:
            console.print(f"\n[{INK_LIGHT}]No results match '{query}'.[/]")
            console.print(
                f"[{INK_LIGHT}]Try a broader search or remove filters.[/]"
            )
    elif not filtered and not query:
        console.print(f"\n[{INK_LIGHT}]No reports match the given filters.[/]")
        console.print(
            f"[{INK_LIGHT}]Try a broader search or remove filters.[/]"
        )

    console.print()
