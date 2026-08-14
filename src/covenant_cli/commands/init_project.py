"""covenant init <name> -- create a governed project scaffold."""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from covenant_cli.templates import get_project_template_dir, get_api_template_dir, get_webapp_template_dir
from covenant_cli.rules import get_rules_dir
from covenant_cli.adapters import list_sdks, get_sdk_info
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


VALID_TEMPLATES = ("default", "api", "webapp")


def _create_governance_scaffold(project_dir: Path, context: dict, tree, sdk: str | None):
    """Create the governance files shared by all templates: registry, memory, rules."""
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
    if sdk:
        registry_data["defaultSdk"] = sdk
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


def _init_default(project_dir: Path, context: dict, tree, sdk: str | None):
    """Create the default governed project scaffold."""
    template_dir = get_project_template_dir()
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )

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

    # --- Governance scaffold ---
    _create_governance_scaffold(project_dir, context, tree, sdk)

    # --- Validation ---
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
    return [p for p in expected_paths if not p.exists()]


def _init_api(project_dir: Path, context: dict, tree, sdk: str | None):
    """Create a FastAPI governed agent API scaffold."""
    # Render GOVERNANCE.md from the default project template (shared)
    project_env = Environment(
        loader=FileSystemLoader(str(get_project_template_dir())),
        keep_trailing_newline=True,
    )
    governance_content = _render_template(project_env, "GOVERNANCE.md.j2", context)
    (project_dir / "GOVERNANCE.md").write_text(governance_content, encoding="utf-8")
    tree.add(file_added("GOVERNANCE.md"))

    # Render API templates
    api_dir = get_api_template_dir()
    env = Environment(
        loader=FileSystemLoader(str(api_dir)),
        keep_trailing_newline=True,
    )

    # --- Root files ---
    root_files = {
        "main.py": _render_template(env, "main.py.j2", context),
        "requirements.txt": _render_template(env, "requirements.txt.j2", context),
        ".env.example": _render_template(env, ".env.example.j2", context),
        "runner.py": _render_template(env, "runner.py.j2", context),
    }
    for filename, content in root_files.items():
        filepath = project_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(filename))

    # --- routers/ ---
    routers_dir = project_dir / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)
    router_files = {
        "__init__.py": _render_template(env, "routers/__init__.py.j2", context),
        "services.py": _render_template(env, "routers/services.py.j2", context),
        "runs.py": _render_template(env, "routers/runs.py.j2", context),
        "health.py": _render_template(env, "routers/health.py.j2", context),
    }
    for filename, content in router_files.items():
        filepath = routers_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(f"routers/{filename}"))

    # --- models/ ---
    models_dir = project_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_files = {
        "__init__.py": _render_template(env, "models/__init__.py.j2", context),
        "schemas.py": _render_template(env, "models/schemas.py.j2", context),
        "database.py": _render_template(env, "models/database.py.j2", context),
    }
    for filename, content in model_files.items():
        filepath = models_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(f"models/{filename}"))

    # --- Governance scaffold ---
    _create_governance_scaffold(project_dir, context, tree, sdk)

    # --- Validation ---
    expected_paths = [
        project_dir / "GOVERNANCE.md",
        project_dir / "main.py",
        project_dir / "requirements.txt",
        project_dir / "runner.py",
        project_dir / "routers" / "__init__.py",
        project_dir / "routers" / "services.py",
        project_dir / "routers" / "runs.py",
        project_dir / "routers" / "health.py",
        project_dir / "models" / "__init__.py",
        project_dir / "models" / "schemas.py",
        project_dir / "models" / "database.py",
        project_dir / "registry" / "agents.json",
        project_dir / "memory" / "inheritance" / "README.md",
        project_dir / "memory" / "memos" / "README.md",
    ]
    return [p for p in expected_paths if not p.exists()]


def _init_webapp(project_dir: Path, context: dict, tree, sdk: str | None):
    """Create a Django webapp governed agent scaffold."""
    # Generate Django secret key and add to context
    context["django_secret_key"] = secrets.token_urlsafe(50)

    # Render GOVERNANCE.md from the default project template (shared)
    project_env = Environment(
        loader=FileSystemLoader(str(get_project_template_dir())),
        keep_trailing_newline=True,
    )
    governance_content = _render_template(project_env, "GOVERNANCE.md.j2", context)
    (project_dir / "GOVERNANCE.md").write_text(governance_content, encoding="utf-8")
    tree.add(file_added("GOVERNANCE.md"))

    # Render webapp templates
    webapp_dir = get_webapp_template_dir()
    env = Environment(
        loader=FileSystemLoader(str(webapp_dir)),
        keep_trailing_newline=True,
    )

    # --- Root files ---
    root_files = {
        "manage.py": _render_template(env, "manage.py.j2", context),
        "requirements.txt": _render_template(env, "requirements.txt.j2", context),
        ".env.example": _render_template(env, ".env.example.j2", context),
    }
    for filename, content in root_files.items():
        filepath = project_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(filename))

    # --- config/ ---
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_files = {
        "__init__.py": _render_template(env, "config/__init__.py.j2", context),
        "settings.py": _render_template(env, "config/settings.py.j2", context),
        "urls.py": _render_template(env, "config/urls.py.j2", context),
        "wsgi.py": _render_template(env, "config/wsgi.py.j2", context),
    }
    for filename, content in config_files.items():
        filepath = config_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(f"config/{filename}"))

    # --- core/ ---
    core_dir = project_dir / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    core_files = {
        "__init__.py": _render_template(env, "core/__init__.py.j2", context),
        "models.py": _render_template(env, "core/models.py.j2", context),
        "admin.py": _render_template(env, "core/admin.py.j2", context),
        "apps.py": _render_template(env, "core/apps.py.j2", context),
    }
    for filename, content in core_files.items():
        filepath = core_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(f"core/{filename}"))

    migrations_dir = core_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (migrations_dir / "__init__.py").write_text("", encoding="utf-8")
    tree.add(file_added("core/migrations/__init__.py"))

    # --- dashboard/ ---
    dash_dir = project_dir / "dashboard"
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_files = {
        "__init__.py": _render_template(env, "dashboard/__init__.py.j2", context),
        "apps.py": _render_template(env, "dashboard/apps.py.j2", context),
        "urls.py": _render_template(env, "dashboard/urls.py.j2", context),
        "views.py": _render_template(env, "dashboard/views.py.j2", context),
        "runner.py": _render_template(env, "dashboard/runner.py.j2", context),
    }
    for filename, content in dash_files.items():
        filepath = dash_dir / filename
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(f"dashboard/{filename}"))

    # --- templates/ (Django HTML templates) ---
    tmpl_dir = project_dir / "templates"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    tmpl_dash_dir = tmpl_dir / "dashboard"
    tmpl_dash_dir.mkdir(parents=True, exist_ok=True)

    html_files = {
        "templates/base.html": _render_template(env, "templates/base.html.j2", context),
        "templates/dashboard/index.html": _render_template(env, "templates/dashboard/index.html.j2", context),
        "templates/dashboard/service_detail.html": _render_template(env, "templates/dashboard/service_detail.html.j2", context),
        "templates/dashboard/run_detail.html": _render_template(env, "templates/dashboard/run_detail.html.j2", context),
        "templates/dashboard/pipeline_results.html": _render_template(env, "templates/dashboard/pipeline_results.html.j2", context),
    }
    for rel_path, content in html_files.items():
        filepath = project_dir / rel_path
        filepath.write_text(content, encoding="utf-8")
        tree.add(file_added(rel_path))

    # --- static/ ---
    static_css_dir = project_dir / "static" / "css"
    static_css_dir.mkdir(parents=True, exist_ok=True)
    css_content = _render_template(env, "static/css/style.css.j2", context)
    (static_css_dir / "style.css").write_text(css_content, encoding="utf-8")
    tree.add(file_added("static/css/style.css"))

    # --- Governance scaffold (registry, memory, IDE rules, services) ---
    _create_governance_scaffold(project_dir, context, tree, sdk)

    # --- Validation ---
    expected_paths = [
        project_dir / "GOVERNANCE.md",
        project_dir / "manage.py",
        project_dir / "requirements.txt",
        project_dir / "config" / "settings.py",
        project_dir / "config" / "urls.py",
        project_dir / "core" / "models.py",
        project_dir / "core" / "admin.py",
        project_dir / "core" / "migrations" / "__init__.py",
        project_dir / "dashboard" / "views.py",
        project_dir / "dashboard" / "runner.py",
        project_dir / "dashboard" / "urls.py",
        project_dir / "templates" / "base.html",
        project_dir / "templates" / "dashboard" / "index.html",
        project_dir / "static" / "css" / "style.css",
        project_dir / "registry" / "agents.json",
        project_dir / "memory" / "inheritance" / "README.md",
        project_dir / "memory" / "memos" / "README.md",
    ]
    return [p for p in expected_paths if not p.exists()]


@click.command()
@click.argument("name")
@click.option(
    "--sdk",
    type=click.Choice(list_sdks()),
    default=None,
    help="Default SDK for services (openai, crewai, langgraph).",
)
@click.option(
    "--template",
    "template_name",
    type=click.Choice(["default", "api", "webapp"]),
    default="default",
    help="Application template: default (CLI project), api (FastAPI), webapp (Django).",
)
def init_command(name: str, sdk: str | None, template_name: str):
    """Create a new governed project.

    NAME is the project directory name (e.g., my-agent-project).
    Use --template to choose an application type (default, api, webapp).
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
        "sdk": sdk,
    }

    # Build output tree for display
    tree = branded_tree(f"{name}/")

    # Dispatch to the right template initializer
    if template_name == "api":
        missing_files = _init_api(project_dir, context, tree, sdk)
    elif template_name == "webapp":
        missing_files = _init_webapp(project_dir, context, tree, sdk)
    else:
        missing_files = _init_default(project_dir, context, tree, sdk)

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

    # Template-specific next steps
    if template_name == "api":
        console.print(
            branded_panel(
                f"[bold {GOLD}]API project created.[/]\n\n"
                f"  [{INK_LIGHT}]cd {name}[/]\n"
                f"  [{INK_LIGHT}]pip install -r requirements.txt[/]\n"
                f"  [{INK_LIGHT}]uvicorn main:app --reload[/]\n\n"
                f"  [{INK_LIGHT}]Then visit http://127.0.0.1:8000/docs for the interactive API.[/]\n\n"
                f"Read [bold]GOVERNANCE.md[/] [{INK_LIGHT}]-- it's the law.[/]",
                title="Next Steps",
            )
        )
    elif template_name == "webapp":
        console.print(
            branded_panel(
                f"[bold {GOLD}]Webapp project created.[/]\n\n"
                f"  [{INK_LIGHT}]cd {name}[/]\n"
                f"  [{INK_LIGHT}]pip install -r requirements.txt[/]\n"
                f"  [{INK_LIGHT}]python manage.py migrate[/]\n"
                f"  [{INK_LIGHT}]python manage.py runserver[/]\n\n"
                f"  [{INK_LIGHT}]Then visit http://127.0.0.1:8000/ for the governance dashboard.[/]\n"
                f"  [{INK_LIGHT}]Register services in /admin/ (create a superuser first).[/]\n\n"
                f"Read [bold]GOVERNANCE.md[/] [{INK_LIGHT}]-- it's the law.[/]",
                title="Next Steps",
            )
        )
    else:
        sdk_info = get_sdk_info(sdk) if sdk else None
        sdk_line = (
            f"  [{INK_LIGHT}]SDK: {sdk_info['label']}[/]\n\n"
            if sdk_info
            else f"  [{INK_LIGHT}]Optional: pip install openai-agents[/]\n\n"
        )
        console.print(
            branded_panel(
                f"[bold {GOLD}]Project created.[/]\n\n"
                f"  [{INK_LIGHT}]cd {name}[/]\n"
                f"  [{INK_LIGHT}]pip install -e .[/]\n"
                f"  [{INK_LIGHT}]covenant add-service my-first-agent[/]\n"
                f"  [{INK_LIGHT}]covenant status[/]\n\n"
                + sdk_line
                + f"Read [bold]GOVERNANCE.md[/] [{INK_LIGHT}]-- it's the law.[/]",
                title="Next Steps",
            )
        )
