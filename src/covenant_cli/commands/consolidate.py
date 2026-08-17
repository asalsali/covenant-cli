"""covenant consolidate -- distill exit reports into summaries."""

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
    print_error,
    print_success,
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


def _format_tokens(n: int) -> str:
    """Format a token count for display (e.g. 1234 -> '1.2K')."""
    if n <= 0:
        return "0"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


def _load_exit_reports(project_root: Path) -> list[tuple[Path, dict]]:
    """Load all JSON exit reports from memory/inheritance/.

    Returns list of (file_path, parsed_data) tuples, sorted oldest first.
    """
    inheritance_dir = project_root / "memory" / "inheritance"
    if not inheritance_dir.exists():
        return []

    results = []
    for json_file in sorted(inheritance_dir.glob("*.json"), key=lambda f: f.stat().st_mtime):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            results.append((json_file, data))
        except (json.JSONDecodeError, OSError):
            continue

    return results


def _top_strings(items: list[str], n: int = 3) -> list[str]:
    """Return the top n most common strings from a flat list."""
    if not items:
        return []
    counter = Counter(items)
    return [item for item, _count in counter.most_common(n)]


def _build_service_summaries(
    reports: list[tuple[Path, dict]],
) -> dict[str, dict]:
    """Group reports by service and compute per-service stats."""
    by_service: dict[str, list[tuple[Path, dict]]] = {}
    for path, data in reports:
        service = data.get("service", "unknown")
        by_service.setdefault(service, []).append((path, data))

    summaries: dict[str, dict] = {}

    for service, svc_reports in sorted(by_service.items()):
        total = len(svc_reports)
        completed = sum(1 for _, d in svc_reports if d.get("status") == "completed")
        failed = sum(1 for _, d in svc_reports if d.get("status") == "failed")
        success_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

        # Duration
        durations = [
            d.get("duration_seconds", 0)
            for _, d in svc_reports
            if isinstance(d.get("duration_seconds"), (int, float))
            and d.get("duration_seconds", 0) > 0
        ]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

        # Tokens and cost
        total_tokens = 0
        total_cost = 0.0
        for _, d in svc_reports:
            usage = d.get("usage")
            if usage and isinstance(usage, dict):
                total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                total_cost += usage.get("total_cost", 0.0)

        total_cost = round(total_cost, 4)

        # Recurring failures
        all_failures: list[str] = []
        for _, d in svc_reports:
            wf = d.get("what_failed", [])
            if isinstance(wf, list):
                all_failures.extend(str(f) for f in wf if f)
            elif isinstance(wf, str) and wf:
                all_failures.append(wf)

        # Top recommendations
        all_recs: list[str] = []
        for _, d in svc_reports:
            recs = d.get("recommendations", [])
            if isinstance(recs, list):
                all_recs.extend(str(r) for r in recs if r)
            elif isinstance(recs, str) and recs:
                all_recs.append(recs)

        # Last run
        timestamps = [d.get("timestamp", "") for _, d in svc_reports if d.get("timestamp")]
        last_run = max(timestamps) if timestamps else None

        summaries[service] = {
            "total_runs": total,
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "recurring_failures": _top_strings(all_failures),
            "top_recommendations": _top_strings(all_recs),
            "last_run": last_run,
            "_reports": svc_reports,  # internal, stripped before output
        }

    return summaries


def _archive_old_reports(
    summaries: dict[str, dict],
    project_root: Path,
) -> int:
    """Move old exit reports to archive, keeping the 5 most recent per service.

    Returns the number of files archived.
    """
    archive_dir = project_root / "memory" / "inheritance" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = 0
    for _service, stats in summaries.items():
        svc_reports: list[tuple[Path, dict]] = stats["_reports"]
        # Reports are already sorted oldest-first from _load_exit_reports
        # Keep the last 5 (most recent), archive the rest
        if len(svc_reports) <= 5:
            continue
        to_archive = svc_reports[:-5]
        for path, _data in to_archive:
            dest = archive_dir / path.name
            shutil.move(str(path), str(dest))
            archived += 1

    return archived


def _print_summary(summaries: dict[str, dict], report_count: int, archived: int) -> None:
    """Print the branded consolidation summary."""
    console.print()
    console.print(branded_panel(
        f"[{INK_LIGHT}]Distilling {report_count} exit reports...[/]",
        title="Consolidation",
    ))
    console.print()

    for service, stats in summaries.items():
        success = stats["success_rate"]
        if success >= 90:
            rate_color = GREEN
        elif success >= 70:
            rate_color = GOLD
        else:
            rate_color = OXBLOOD

        tokens_display = _format_tokens(stats["total_tokens"])

        console.print(
            f"  [bold {GOLD}]{service}[/][{INK_LIGHT}]:[/] "
            f"[{INK_LIGHT}]{stats['total_runs']} runs[/] "
            f"([{rate_color}]{success}% success[/])"
            f"[{INK_LIGHT}], avg {stats['avg_duration']}s, "
            f"{tokens_display} tokens[/]"
        )

        # Failures
        failures = stats["recurring_failures"]
        if failures:
            formatted = ", ".join(failures)
            console.print(f"    [{OXBLOOD}]Top failures:[/] [{INK_LIGHT}]{formatted}[/]")
        else:
            console.print(f"    [{INK_LIGHT}]No recurring failures.[/]")

        # Recommendations
        recs = stats["top_recommendations"]
        if recs:
            formatted = ", ".join(recs)
            console.print(f"    [{GREEN}]Recommendations:[/] [{INK_LIGHT}]{formatted}[/]")

        console.print()

    # Footer
    parts = [f"Consolidated {report_count} reports."]
    if archived > 0:
        parts.append(f"Archived {archived}.")
    print_success("  " + " ".join(parts))
    console.print()


def _update_freshness(reports_dir: Path, consolidation_count: int) -> None:
    """Update freshness scores on all exit reports in the directory.

    effectiveScore = baseScore * 0.5^(consolidation_count / decay_period)
    where decay_period is 10 for standard, 20 for slow.
    """
    if not reports_dir.exists():
        return

    for json_file in reports_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        freshness = data.get("freshness", {})
        base_score = freshness.get("baseScore", 1.0)
        decay_rate = freshness.get("decayRate", "standard")
        last_ref = freshness.get("lastReferencedAt")

        decay_period = 20 if decay_rate == "slow" else 10
        effective = round(base_score * (0.5 ** (consolidation_count / decay_period)), 4)

        data["freshness"] = {
            "baseScore": base_score,
            "effectiveScore": effective,
            "decayRate": decay_rate,
            "lastReferencedAt": last_ref,
        }

        json_file.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )


def _update_baselines(summaries: dict[str, dict], project_root: Path) -> list[str]:
    """Record or compare performance baselines per service.

    On first successful run per service, record baseline.
    On subsequent consolidations, flag >30% drift (worse direction only).
    Returns list of warning strings for drifted metrics.
    """
    baselines_path = project_root / "registry" / "baselines.json"
    baselines_path.parent.mkdir(parents=True, exist_ok=True)

    baselines: dict[str, dict] = {}
    if baselines_path.exists():
        try:
            baselines = json.loads(baselines_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            baselines = {}

    now = datetime.now(timezone.utc).isoformat()
    warnings: list[str] = []

    for service, stats in summaries.items():
        total = stats["total_runs"]
        if total == 0:
            continue

        success_rate = stats["success_rate"] / 100.0  # normalize to 0-1
        avg_duration = stats["avg_duration"]
        avg_tokens = (
            stats["total_tokens"] / total if total > 0 else 0.0
        )

        if service not in baselines:
            # First successful consolidation -- record baseline
            baselines[service] = {
                "avgDuration": avg_duration,
                "successRate": success_rate,
                "avgTokensPerRun": round(avg_tokens, 1),
                "setAt": now,
                "totalRunsAtBaseline": total,
            }
            continue

        # Compare current stats to baseline
        bl = baselines[service]
        bl_dur = bl.get("avgDuration", 0)
        bl_rate = bl.get("successRate", 0)
        bl_tokens = bl.get("avgTokensPerRun", 0)

        # Duration increased >30%
        if bl_dur > 0 and avg_duration > bl_dur * 1.3:
            pct = round((avg_duration - bl_dur) / bl_dur * 100)
            warnings.append(
                f"{service}: duration +{pct}% above baseline "
                f"(avg {bl_dur:.1f}s -> {avg_duration:.1f}s)"
            )

        # Success rate decreased >30% (relative)
        if bl_rate > 0 and success_rate < bl_rate * 0.7:
            pct = round((bl_rate - success_rate) / bl_rate * 100)
            warnings.append(
                f"{service}: success rate -{pct}% below baseline "
                f"({bl_rate:.0%} -> {success_rate:.0%})"
            )

        # Token consumption increased >30%
        if bl_tokens > 0 and avg_tokens > bl_tokens * 1.3:
            pct = round((avg_tokens - bl_tokens) / bl_tokens * 100)
            warnings.append(
                f"{service}: token consumption +{pct}% above baseline "
                f"(avg {bl_tokens:.0f} -> {avg_tokens:.0f})"
            )

    baselines_path.write_text(
        json.dumps(baselines, indent=2) + "\n",
        encoding="utf-8",
    )

    return warnings


def _compute_trust(summaries: dict[str, dict], project_root: Path) -> None:
    """Compute and write trust levels for each service.

    Trust levels:
      0 = Untested (default)
      1 = Proven   (3+ runs, >70% success)
      2 = Trusted  (10+ runs, >85% success)
      3 = Veteran  (25+ runs, >90% success)

    Demotion: if 2+ of the last 5 runs failed, drop one level.
    """
    now = datetime.now(timezone.utc).isoformat()
    trust: dict[str, dict] = {}

    for service, stats in summaries.items():
        total = stats["total_runs"]
        success_rate = stats["success_rate"]

        # Determine base level from thresholds
        level = 0
        if total >= 25 and success_rate > 90:
            level = 3
        elif total >= 10 and success_rate > 85:
            level = 2
        elif total >= 3 and success_rate > 70:
            level = 1

        # Demotion check: count failures in last 5 reports
        svc_reports: list[tuple[Path, dict]] = stats.get("_reports", [])
        recent = svc_reports[-5:] if len(svc_reports) >= 5 else svc_reports
        recent_failures = sum(
            1 for _, d in recent if d.get("status") == "failed"
        )
        if recent_failures >= 2 and level > 0:
            level -= 1

        labels = {0: "Untested", 1: "Proven", 2: "Trusted", 3: "Veteran"}
        trust[service] = {
            "level": level,
            "label": labels[level],
            "totalRuns": total,
            "successRate": success_rate,
            "updatedAt": now,
        }

    trust_path = project_root / "registry" / "trust.json"
    trust_path.parent.mkdir(parents=True, exist_ok=True)
    trust_path.write_text(
        json.dumps(trust, indent=2) + "\n",
        encoding="utf-8",
    )


@click.command()
@click.option("--archive", is_flag=True, help="Archive old exit reports (keep last 5 per service)")
def consolidate_command(archive):
    """Distill exit reports into summaries."""
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    reports = _load_exit_reports(project_root)
    if not reports:
        print_error("Nothing to consolidate.")
        raise SystemExit(0)

    summaries = _build_service_summaries(reports)

    # Archive if requested
    archived = 0
    if archive:
        archived = _archive_old_reports(summaries, project_root)
        if archived > 0:
            console.print(
                f"\n  [{INK_LIGHT}]Archived {archived} reports to "
                f"memory/inheritance/archive/[/]"
            )

    # Write consolidated summary file
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%dT%H%M%S")

    output_data = {
        "timestamp": now.isoformat(),
        "services": {},
        "report_count": len(reports),
        "archived": archived,
    }

    for service, stats in summaries.items():
        output_data["services"][service] = {
            "total_runs": stats["total_runs"],
            "completed": stats["completed"],
            "failed": stats["failed"],
            "success_rate": stats["success_rate"],
            "avg_duration": stats["avg_duration"],
            "total_tokens": stats["total_tokens"],
            "total_cost": stats["total_cost"],
            "recurring_failures": stats["recurring_failures"],
            "top_recommendations": stats["top_recommendations"],
            "last_run": stats["last_run"],
        }

    memory_dir = project_root / "memory"
    output_path = memory_dir / f"consolidated-{timestamp_str}.json"
    output_path.write_text(
        json.dumps(output_data, indent=2) + "\n",
        encoding="utf-8",
    )

    # Update freshness scores on all exit reports
    inheritance_dir = memory_dir / "inheritance"
    consolidation_count = len(list(memory_dir.glob("consolidated-*.json")))
    _update_freshness(inheritance_dir, consolidation_count)

    # Compute and write service trust levels
    _compute_trust(summaries, project_root)

    # Update baselines and detect regression drift
    drift_warnings = _update_baselines(summaries, project_root)

    _print_summary(summaries, len(reports), archived)

    # Display drift warnings
    if drift_warnings:
        for warning in drift_warnings:
            console.print(f"  [{GOLD}]DRIFT:[/] [{OXBLOOD}]{warning}[/]")
        console.print()
