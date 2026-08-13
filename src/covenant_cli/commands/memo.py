"""covenant memo -- cross-service communication via structured memos."""

import json
from datetime import datetime, timezone
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
    branded_table,
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


def _load_registry(project_root: Path) -> dict:
    """Load the agent registry."""
    registry_path = project_root / "registry" / "agents.json"
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _get_service_slugs(registry: dict) -> list[str]:
    """Extract all service slugs from the registry."""
    return [svc.get("slug", "") for svc in registry.get("services", [])]


def _memos_dir(project_root: Path) -> Path:
    """Return the memos directory, creating it if needed."""
    memos = project_root / "memory" / "memos"
    memos.mkdir(parents=True, exist_ok=True)
    return memos


def _load_memo(path: Path) -> dict | None:
    """Load a single memo JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _all_memo_files(memos_dir: Path) -> list[Path]:
    """List all memo JSON files, excluding non-memo files."""
    if not memos_dir.exists():
        return []
    return sorted(
        (f for f in memos_dir.glob("*.json") if f.name != "README.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def _truncate(text: str, length: int = 60) -> str:
    """Truncate text to a given length, adding ellipsis if needed."""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


@click.group()
def memo_command():
    """Cross-service communication via structured memos."""
    pass


@memo_command.command("send")
@click.argument("from_service")
@click.argument("to_service")
@click.argument("message")
def send_memo(from_service, to_service, message):
    """Send a memo from one service to another.

    FROM_SERVICE is the sender. TO_SERVICE is the recipient.
    MESSAGE is the memo content (quote multi-word messages).
    """
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    # Validate services exist in registry (warn but proceed)
    registry = _load_registry(project_root)
    slugs = _get_service_slugs(registry)

    if from_service not in slugs:
        console.print(
            f"  [{OXBLOOD}]![/] [{INK_LIGHT}]Service '{from_service}' "
            f"not found in registry. Memo will still be written.[/]"
        )
    if to_service not in slugs:
        console.print(
            f"  [{OXBLOOD}]![/] [{INK_LIGHT}]Service '{to_service}' "
            f"not found in registry. Memo will still be written.[/]"
        )

    # Build the memo
    now = datetime.now(timezone.utc)
    memo = {
        "from": from_service,
        "to": to_service,
        "timestamp": now.isoformat(),
        "message": message,
        "read": False,
    }

    # Write to disk
    memos_dir = _memos_dir(project_root)
    timestamp_slug = now.strftime("%Y%m%dT%H%M%S")
    filename = f"{from_service}-to-{to_service}-{timestamp_slug}.json"
    memo_path = memos_dir / filename
    memo_path.write_text(
        json.dumps(memo, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    console.print()
    print_success(f"Memo sent from {from_service} to {to_service}.")
    console.print(f"  [{INK_LIGHT}]{memo_path.relative_to(project_root)}[/]")
    console.print()


@memo_command.command("list")
def list_memos():
    """List all memos in the project."""
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    memos_dir = _memos_dir(project_root)
    memo_files = _all_memo_files(memos_dir)

    if not memo_files:
        console.print(
            f"\n[{INK_LIGHT}]No memos found.[/]"
        )
        console.print(
            f"[{INK_LIGHT}]Send one with: "
            f"covenant memo send <from> <to> <message>[/]"
        )
        return

    # Load all memos and count unread
    memos = []
    for f in memo_files:
        data = _load_memo(f)
        if data is not None:
            data["_path"] = f
            memos.append(data)

    unread = sum(1 for m in memos if not m.get("read", False))

    # Header
    console.print()
    console.print(
        branded_panel(
            f"[{INK_LIGHT}]{len(memos)} memo(s), "
            f"[bold {GOLD}]{unread} unread[/bold {GOLD}][/]",
            title="Memos",
        )
    )

    # Sort by timestamp descending (already sorted by mtime, but sort by
    # the JSON timestamp for correctness)
    memos.sort(key=lambda m: m.get("timestamp", ""), reverse=True)

    # Table
    table = branded_table(
        "All Memos",
        columns=[
            ("From", f"bold {GOLD}"),
            ("To", f"bold {GOLD}"),
            ("Timestamp", INK_LIGHT),
            ("Read", "bold"),
            ("Message", INK_LIGHT),
        ],
    )

    for m in memos:
        read_status = (
            f"[{GREEN}]yes[/]" if m.get("read", False)
            else f"[{OXBLOOD}]no[/]"
        )
        table.add_row(
            m.get("from", "?"),
            m.get("to", "?"),
            m.get("timestamp", "?"),
            read_status,
            _truncate(m.get("message", ""), 60),
        )

    console.print()
    console.print(table)
    console.print()


@memo_command.command("read")
@click.argument("service")
def read_memos(service):
    """Read all memos addressed to a service and mark them as read.

    SERVICE is the recipient to filter by.
    """
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    memos_dir = _memos_dir(project_root)
    memo_files = _all_memo_files(memos_dir)

    # Filter to memos addressed to this service
    addressed = []
    for f in memo_files:
        data = _load_memo(f)
        if data is not None and data.get("to") == service:
            data["_path"] = f
            addressed.append(data)

    if not addressed:
        console.print(f"\n[{INK_LIGHT}]No memos for {service}.[/]")
        console.print(
            f"[{INK_LIGHT}]Send one with: "
            f"covenant memo send <from> {service} <message>[/]"
        )
        return

    # Sort by timestamp descending
    addressed.sort(key=lambda m: m.get("timestamp", ""), reverse=True)

    console.print()
    console.print(
        branded_panel(
            f"[{INK_LIGHT}]{len(addressed)} memo(s) for "
            f"[bold {GOLD}]{service}[/bold {GOLD}][/]",
            title=f"Memos for {service}",
        )
    )

    for m in addressed:
        was_unread = not m.get("read", False)
        sender = m.get("from", "?")
        timestamp = m.get("timestamp", "?")
        message = m.get("message", "")

        unread_badge = f" [{OXBLOOD}](new)[/]" if was_unread else ""

        console.print()
        console.print(
            f"  [bold {GOLD}]{sender}[/]  "
            f"[{INK_LIGHT}]{timestamp}[/]{unread_badge}"
        )
        console.print(f"  [{INK_LIGHT}]{message}[/]")

        # Mark as read
        if was_unread:
            m["read"] = True
            memo_path = m["_path"]
            # Write back without the internal _path key
            write_data = {k: v for k, v in m.items() if not k.startswith("_")}
            memo_path.write_text(
                json.dumps(write_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    console.print()
    marked = sum(1 for m in addressed if "_path" in m)
    newly_read = sum(
        1 for m in addressed
        if m.get("read", False) and "_path" in m
    )
    if newly_read > 0:
        print_success(f"Marked {newly_read} memo(s) as read.")
    console.print()
