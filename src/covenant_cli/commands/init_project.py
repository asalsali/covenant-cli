"""covenant init <name> -- create a governed project scaffold."""

import json
from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from covenant_cli.templates import get_project_template_dir
from covenant_cli.rules import get_rules_dir

console = Console()


BANNER = r"""
   ___                                  _
  / __\___  __   _____ _ __   __ _ _ __ | |_
 / /  / _ \ \ \ / / _ \ '_ \ / _` | '_ \| __|
/ /__| (_) | \ V /  __/ | | | (_| | | | | |_
\____/\___/   \_/ \___|_| |_|\__,_|_| |_|\__|

  Governed agents. From the first line.
"""


def _render_template(env: Environment, template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    template = env.get_template(template_name)
    return template.render(**context)


def _write_file(path: Path, content: str, tree: Tree) -> None:
    """Write a file and add it to the output tree."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    tree.add(f"[green]+[/green] {path.relative_to(path.parent.parent) if path.parent.parent.exists() else path.name}")


@click.command()
@click.argument("name")
def init_command(name: str):
    """Create a new governed project.

    NAME is the project directory name (e.g., my-agent-project).
    """
    project_dir = Path.cwd() / name

    if project_dir.exists() and any(project_dir.iterdir()):
        console.print(f"[red]Directory '{name}' already exists and is not empty.[/red]")
        raise SystemExit(1)

    project_dir.mkdir(parents=True, exist_ok=True)

    # Prepare template context
    context = {
        "project_name": name,
        "project_slug": name.replace("-", "_").replace(" ", "_").lower(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Set up Jinja2
    template_dir = get_project_template_dir()
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )

    # Build output tree for display
    tree = Tree(f"[bold blue]{name}/[/bold blue]")

    # --- Root files ---
    files = {
        "GOVERNANCE.md": _render_template(env, "GOVERNANCE.md.j2", context),
        "pyproject.toml": _render_template(env, "pyproject.toml.j2", context),
        "README.md": _render_template(env, "README.md.j2", context),
        ".env.example": _render_template(env, "env_example.j2", context),
    }
    for filename, content in files.items():
        filepath = project_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(f"[green]+[/green] {filename}")

    # --- src/ ---
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text('"""' + context["project_slug"] + ' -- governed agent project."""\n', encoding="utf-8")
    tree.add(f"[green]+[/green] src/__init__.py")

    main_content = _render_template(env, "main.py.j2", context)
    (src_dir / "main.py").write_text(main_content, encoding="utf-8")
    tree.add(f"[green]+[/green] src/main.py")

    # --- Registry ---
    registry_dir = project_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_data = {
        "agents": [],
        "services": [],
        "lastUpdated": None,
    }
    (registry_dir / "agents.json").write_text(
        json.dumps(registry_data, indent=2) + "\n", encoding="utf-8"
    )
    tree.add(f"[green]+[/green] registry/agents.json")

    # --- Memory ---
    inheritance_dir = project_dir / "memory" / "inheritance"
    inheritance_dir.mkdir(parents=True, exist_ok=True)
    (inheritance_dir / "README.md").write_text(
        "# Inheritance\n\nExit reports from prior service runs live here.\n\n"
        "Each run writes a JSON file with what worked, what failed, and recommendations.\n"
        "New agents read these before acting.\n",
        encoding="utf-8",
    )
    tree.add(f"[green]+[/green] memory/inheritance/README.md")

    memos_dir = project_dir / "memory" / "memos"
    memos_dir.mkdir(parents=True, exist_ok=True)
    (memos_dir / "README.md").write_text(
        "# Memos\n\nCross-service communication lives here.\n\n"
        "Services write structured memos to coordinate with other services.\n"
        "Memos are pull-based -- the reader checks when ready.\n",
        encoding="utf-8",
    )
    tree.add(f"[green]+[/green] memory/memos/README.md")

    # --- Convention rules (.cursor/rules and .claude/rules) ---
    rules_dir = get_rules_dir()
    governance_mdc = (rules_dir / "governance.mdc").read_text(encoding="utf-8")
    agent_patterns_mdc = (rules_dir / "agent-patterns.mdc").read_text(encoding="utf-8")

    for ide_dir_name in [".cursor/rules", ".claude/rules"]:
        ide_dir = project_dir / ide_dir_name
        ide_dir.mkdir(parents=True, exist_ok=True)
        (ide_dir / "governance.mdc").write_text(governance_mdc, encoding="utf-8")
        (ide_dir / "agent-patterns.mdc").write_text(agent_patterns_mdc, encoding="utf-8")
        tree.add(f"[green]+[/green] {ide_dir_name}/governance.mdc")
        tree.add(f"[green]+[/green] {ide_dir_name}/agent-patterns.mdc")

    # --- Services dir placeholder ---
    services_dir = project_dir / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    (services_dir / ".gitkeep").write_text("", encoding="utf-8")

    # --- Output ---
    console.print()
    console.print(Panel(BANNER, style="bold cyan", expand=False))
    console.print()
    console.print(tree)
    console.print()
    console.print(
        Panel(
            "[bold green]Project created.[/bold green]\n\n"
            f"  [dim]cd {name}[/dim]\n"
            "  [dim]pip install -e .[/dim]\n"
            "  [dim]covenant add-service my-first-agent[/dim]\n"
            "  [dim]covenant status[/dim]\n\n"
            "Read [bold]GOVERNANCE.md[/bold] -- it's the law.",
            title="Next Steps",
            expand=False,
        )
    )
