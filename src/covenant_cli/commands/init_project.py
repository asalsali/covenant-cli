"""covenant init <name> -- create a governed project scaffold."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from covenant_cli.templates import get_project_template_dir
from covenant_cli.rules import get_rules_dir
from covenant_cli.theme import (
    console,
    print_banner,
    branded_panel,
    branded_tree,
    file_added,
    print_error,
    GOLD,
    GREEN,
    INK_LIGHT,
    OXBLOOD,
)


def _render_template(env: Environment, template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    template = env.get_template(template_name)
    return template.render(**context)


def _write_file(path: Path, content: str, tree) -> None:
    """Write a file and add it to the output tree."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    rel = path.relative_to(path.parent.parent) if path.parent.parent.exists() else path.name
    tree.add(file_added(str(rel)))


@click.command()
@click.argument("name")
def init_command(name: str):
    """Create a new governed project.

    NAME is the project directory name (e.g., my-agent-project).
    """
    project_dir = Path.cwd() / name

    if project_dir.exists() and any(project_dir.iterdir()):
        print_error(f"Directory '{name}' already exists and is not empty.")
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
    tree = branded_tree(f"{name}/")

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
        tree.add(file_added(filename))

    # --- src/ ---
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text('"""' + context["project_slug"] + ' -- governed agent project."""\n', encoding="utf-8")
    tree.add(file_added("src/__init__.py"))

    main_content = _render_template(env, "main.py.j2", context)
    (src_dir / "main.py").write_text(main_content, encoding="utf-8")
    tree.add(file_added("src/main.py"))

    # --- Compute GOVERNANCE.md hash ---
    governance_path = project_dir / "GOVERNANCE.md"
    governance_hash = hashlib.sha256(
        governance_path.read_bytes()
    ).hexdigest()

    # --- Registry ---
    registry_dir = project_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_data = {
        "agents": [],
        "services": [],
        "lastUpdated": None,
        "governanceHash": governance_hash,
    }
    (registry_dir / "agents.json").write_text(
        json.dumps(registry_data, indent=2) + "\n", encoding="utf-8"
    )
    tree.add(file_added("registry/agents.json"))

    # --- Memory ---
    inheritance_dir = project_dir / "memory" / "inheritance"
    inheritance_dir.mkdir(parents=True, exist_ok=True)
    (inheritance_dir / "README.md").write_text(
        "# Inheritance\n\nExit reports from prior service runs live here.\n\n"
        "Each run writes a JSON file with what worked, what failed, and recommendations.\n"
        "New agents read these before acting.\n",
        encoding="utf-8",
    )
    tree.add(file_added("memory/inheritance/README.md"))

    memos_dir = project_dir / "memory" / "memos"
    memos_dir.mkdir(parents=True, exist_ok=True)
    (memos_dir / "README.md").write_text(
        "# Memos\n\nCross-service communication lives here.\n\n"
        "Services write structured memos to coordinate with other services.\n"
        "Memos are pull-based -- the reader checks when ready.\n",
        encoding="utf-8",
    )
    tree.add(file_added("memory/memos/README.md"))

    # --- Convention rules (.cursor/rules and .claude/rules) ---
    rules_dir = get_rules_dir()
    governance_mdc = (rules_dir / "governance.mdc").read_text(encoding="utf-8")
    agent_patterns_mdc = (rules_dir / "agent-patterns.mdc").read_text(encoding="utf-8")

    for ide_dir_name in [".cursor/rules", ".claude/rules"]:
        ide_dir = project_dir / ide_dir_name
        ide_dir.mkdir(parents=True, exist_ok=True)
        (ide_dir / "governance.mdc").write_text(governance_mdc, encoding="utf-8")
        (ide_dir / "agent-patterns.mdc").write_text(agent_patterns_mdc, encoding="utf-8")
        tree.add(file_added(f"{ide_dir_name}/governance.mdc"))
        tree.add(file_added(f"{ide_dir_name}/agent-patterns.mdc"))

    # --- Services dir placeholder ---
    services_dir = project_dir / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    (services_dir / ".gitkeep").write_text("", encoding="utf-8")

    # --- Post-init validation ---
    expected_paths = [
        project_dir / "GOVERNANCE.md",
        project_dir / "pyproject.toml",
        project_dir / "README.md",
        project_dir / "src" / "__init__.py",
        project_dir / "src" / "main.py",
        project_dir / "registry" / "agents.json",
        project_dir / "memory" / "inheritance" / "README.md",
        project_dir / "memory" / "memos" / "README.md",
        project_dir / "services" / ".gitkeep",
    ]
    missing_files = [p for p in expected_paths if not p.exists()]

    # --- Output ---
    print_banner()
    console.print()
    console.print(tree)
    console.print()

    if missing_files:
        for mf in missing_files:
            rel = mf.relative_to(project_dir)
            console.print(f"  [{OXBLOOD}]![/] [{INK_LIGHT}]Failed to create: {rel}[/]")
        console.print()
    else:
        console.print(f"  [{GREEN}]All files created successfully.[/]")
        console.print()

    console.print(
        branded_panel(
            f"[bold {GOLD}]Project created.[/]\n\n"
            f"  [{INK_LIGHT}]cd {name}[/]\n"
            f"  [{INK_LIGHT}]pip install -e .[/]\n"
            f"  [{INK_LIGHT}]covenant add-service my-first-agent[/]\n"
            f"  [{INK_LIGHT}]covenant status[/]\n\n"
            f"  [{INK_LIGHT}]Optional: pip install openai-agents[/]\n\n"
            f"Read [bold]GOVERNANCE.md[/] [{INK_LIGHT}]-- it's the law.[/]",
            title="Next Steps",
        )
    )
