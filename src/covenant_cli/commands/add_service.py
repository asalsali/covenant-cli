"""covenant add-service <name> -- add a governed service to the project."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

from covenant_cli.adapters import list_sdks, get_sdk_info
from covenant_cli.templates import get_service_template_dir
from covenant_cli.theme import (
    console,
    branded_panel,
    branded_tree,
    file_added,
    print_error,
    GOLD,
    INK_LIGHT,
    OXBLOOD,
)


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


def _resolve_sdk(explicit_sdk: str | None, project_root: Path) -> str | None:
    """Resolve the SDK to use: explicit flag > project default > None."""
    if explicit_sdk:
        return explicit_sdk
    registry_path = project_root / "registry" / "agents.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        return registry.get("defaultSdk")
    except (json.JSONDecodeError, OSError):
        return None


def _update_registry(
    project_root: Path,
    service_name: str,
    service_slug: str,
    sdk: str | None = None,
) -> None:
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
    if sdk:
        service_entry["sdk"] = sdk
    registry["services"].append(service_entry)
    registry["lastUpdated"] = datetime.now(timezone.utc).isoformat()

    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


@click.command()
@click.argument("name")
@click.option(
    "--sdk",
    type=click.Choice(list_sdks()),
    default=None,
    help="SDK for this service (openai, crewai, langgraph). Falls back to project default.",
)
def add_service_command(name: str, sdk: str | None):
    """Add a governed service to the project.

    NAME is the service name (e.g., research-agent). Will be normalized
    to lowercase with underscores.
    """
    project_root = _find_project_root()
    if project_root is None:
        print_error(
            "Not inside a covenant project. "
            "Run [bold]covenant init <name>[/bold] first."
        )
        raise SystemExit(1)

    # Resolve SDK: explicit flag > project default > None (generic)
    resolved_sdk = _resolve_sdk(sdk, project_root)

    service_slug = _normalize_name(name)
    service_class = "".join(word.capitalize() for word in service_slug.split("_"))
    service_dir = project_root / "services" / service_slug

    if service_dir.exists() and any(service_dir.iterdir()):
        print_error(f"Service '{service_slug}' already exists.")
        raise SystemExit(1)

    # Prepare context
    context = {
        "service_name": name,
        "service_slug": service_slug,
        "service_class": service_class,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Set up Jinja2 -- SDK-specific templates take priority over generic
    template_dir = get_service_template_dir()
    if resolved_sdk:
        sdk_template_dir = template_dir / resolved_sdk
        # SDK dir first in search path, generic dir as fallback
        loader = ChoiceLoader([
            FileSystemLoader(str(sdk_template_dir)),
            FileSystemLoader(str(template_dir)),
        ])
    else:
        loader = FileSystemLoader(str(template_dir))
    env = Environment(
        loader=loader,
        keep_trailing_newline=True,
    )

    # Build tree for display
    tree = branded_tree(f"services/{service_slug}/")

    # --- Service files ---
    service_dir.mkdir(parents=True, exist_ok=True)

    # __init__.py
    init_content = env.get_template("init.py.j2").render(**context)
    (service_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    tree.add(file_added("__init__.py"))

    # manager.py
    manager_content = env.get_template("manager.py.j2").render(**context)
    (service_dir / "manager.py").write_text(manager_content, encoding="utf-8")
    tree.add(file_added("manager.py"))

    # tools.py
    tools_content = env.get_template("tools.py.j2").render(**context)
    (service_dir / "tools.py").write_text(tools_content, encoding="utf-8")
    tree.add(file_added("tools.py"))

    # agents/
    agents_dir = service_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "__init__.py").write_text(
        f'"""Agents for the {service_slug} service."""\n', encoding="utf-8"
    )
    tree.add(file_added("agents/__init__.py"))

    agent_content = env.get_template("example_agent.py.j2").render(**context)
    (agents_dir / "example_agent.py").write_text(agent_content, encoding="utf-8")
    tree.add(file_added("agents/example_agent.py"))

    # schemas/
    schemas_dir = service_dir / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "__init__.py").write_text(
        f'"""Schemas for the {service_slug} service."""\n', encoding="utf-8"
    )
    tree.add(file_added("schemas/__init__.py"))

    types_content = env.get_template("types.py.j2").render(**context)
    (schemas_dir / "types.py").write_text(types_content, encoding="utf-8")
    tree.add(file_added("schemas/types.py"))

    # memory/
    memory_dir = service_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "README.md").write_text(
        f"# {name} Memory\n\n"
        "Service-specific exit reports and learnings.\n"
        "The manager writes here after every run.\n",
        encoding="utf-8",
    )
    tree.add(file_added("memory/README.md"))

    # --- Update registry ---
    _update_registry(project_root, name, service_slug, sdk=resolved_sdk)

    # --- Output ---
    console.print()
    console.print(tree)
    console.print()

    sdk_note = ""
    if resolved_sdk:
        sdk_info = get_sdk_info(resolved_sdk)
        sdk_note = f"  [{INK_LIGHT}]SDK: {sdk_info['label']}[/]\n\n"

    console.print(
        branded_panel(
            f"[bold {GOLD}]Service '{service_slug}' registered.[/]\n\n"
            + sdk_note
            + f"  [{INK_LIGHT}]1. Edit services/{service_slug}/agents/example_agent.py[/]\n"
            f"  [{INK_LIGHT}]2. Define types in services/{service_slug}/schemas/types.py[/]\n"
            f"  [{INK_LIGHT}]3. Wire agents in services/{service_slug}/manager.py[/]\n"
            f"  [{INK_LIGHT}]4. Run: covenant status[/]\n\n"
            f"[{INK_LIGHT}]The manager writes exit reports automatically.[/]",
            title="Next Steps",
        )
    )
