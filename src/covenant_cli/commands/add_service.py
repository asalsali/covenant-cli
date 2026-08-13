"""covenant add-service <name> -- add a governed service to the project."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from covenant_cli.templates import get_service_template_dir

console = Console()


def _normalize_name(name: str) -> str:
    """Normalize a service name to lowercase with underscores."""
    normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return normalized


def _find_project_root() -> Path | None:
    """Walk up from cwd to find a directory with registry/agents.json."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "registry" / "agents.json").exists():
            return parent
    return None


def _update_registry(project_root: Path, service_name: str, service_slug: str) -> None:
    """Register the new service in registry/agents.json."""
    registry_path = project_root / "registry" / "agents.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    service_entry = {
        "name": service_name,
        "slug": service_slug,
        "path": f"services/{service_slug}",
        "registeredAt": datetime.now(timezone.utc).isoformat(),
        "lastRun": None,
        "status": "registered",
    }
    registry["services"].append(service_entry)
    registry["lastUpdated"] = datetime.now(timezone.utc).isoformat()

    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


@click.command()
@click.argument("name")
def add_service_command(name: str):
    """Add a governed service to the project.

    NAME is the service name (e.g., research-agent). Will be normalized
    to lowercase with underscores.
    """
    project_root = _find_project_root()
    if project_root is None:
        console.print(
            "[red]Not inside a covenant project.[/red] "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    service_slug = _normalize_name(name)
    service_class = "".join(word.capitalize() for word in service_slug.split("_"))
    service_dir = project_root / "services" / service_slug

    if service_dir.exists() and any(service_dir.iterdir()):
        console.print(f"[red]Service '{service_slug}' already exists.[/red]")
        raise SystemExit(1)

    # Prepare context
    context = {
        "service_name": name,
        "service_slug": service_slug,
        "service_class": service_class,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Set up Jinja2
    template_dir = get_service_template_dir()
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )

    # Build tree for display
    tree = Tree(f"[bold blue]services/{service_slug}/[/bold blue]")

    # --- Service files ---
    service_dir.mkdir(parents=True, exist_ok=True)

    # __init__.py
    init_content = env.get_template("init.py.j2").render(**context)
    (service_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    tree.add(f"[green]+[/green] __init__.py")

    # manager.py
    manager_content = env.get_template("manager.py.j2").render(**context)
    (service_dir / "manager.py").write_text(manager_content, encoding="utf-8")
    tree.add(f"[green]+[/green] manager.py")

    # tools.py
    tools_content = env.get_template("tools.py.j2").render(**context)
    (service_dir / "tools.py").write_text(tools_content, encoding="utf-8")
    tree.add(f"[green]+[/green] tools.py")

    # agents/
    agents_dir = service_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "__init__.py").write_text(
        f'"""Agents for the {service_slug} service."""\n', encoding="utf-8"
    )
    tree.add(f"[green]+[/green] agents/__init__.py")

    agent_content = env.get_template("example_agent.py.j2").render(**context)
    (agents_dir / "example_agent.py").write_text(agent_content, encoding="utf-8")
    tree.add(f"[green]+[/green] agents/example_agent.py")

    # schemas/
    schemas_dir = service_dir / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "__init__.py").write_text(
        f'"""Schemas for the {service_slug} service."""\n', encoding="utf-8"
    )
    tree.add(f"[green]+[/green] schemas/__init__.py")

    types_content = env.get_template("types.py.j2").render(**context)
    (schemas_dir / "types.py").write_text(types_content, encoding="utf-8")
    tree.add(f"[green]+[/green] schemas/types.py")

    # memory/
    memory_dir = service_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "README.md").write_text(
        f"# {name} Memory\n\n"
        "Service-specific exit reports and learnings.\n"
        "The manager writes here after every run.\n",
        encoding="utf-8",
    )
    tree.add(f"[green]+[/green] memory/README.md")

    # --- Update registry ---
    _update_registry(project_root, name, service_slug)

    # --- Output ---
    console.print()
    console.print(tree)
    console.print()
    console.print(
        Panel(
            f"[bold green]Service '{service_slug}' created.[/bold green]\n\n"
            f"  [dim]1. Edit services/{service_slug}/agents/example_agent.py[/dim]\n"
            f"  [dim]2. Define your types in services/{service_slug}/schemas/types.py[/dim]\n"
            f"  [dim]3. Wire agents in services/{service_slug}/manager.py[/dim]\n"
            f"  [dim]4. Run: covenant status[/dim]\n\n"
            "The manager writes exit reports automatically.",
            title="Next Steps",
            expand=False,
        )
    )
