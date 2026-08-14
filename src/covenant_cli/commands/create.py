"""covenant create <description> -- create a governed app from natural language."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import click

from covenant_cli.theme import (
    console,
    branded_panel,
    branded_tree,
    file_added,
    print_error,
    GOLD,
    GREEN,
    INK_LIGHT,
    OXBLOOD,
)


def _normalize_name(name: str) -> str:
    """Lowercase hyphenated to snake_case."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _display_plan(plan: dict, template_name: str) -> None:
    """Display the LLM-generated plan in branded Rich output."""
    console.print()
    console.print(branded_panel(
        f"[bold {GOLD}]Project: {plan['project_name']}[/]\n"
        f"[{INK_LIGHT}]\"{plan['project_description']}\"[/]",
        title="Covenant Create -- Build Plan",
    ))
    console.print()

    # Services
    console.print(f"  [{GOLD}]Services ({len(plan['services'])}):[/]")
    console.print()

    for i, service in enumerate(plan["services"], 1):
        console.print(f"  [{GOLD}]{i}. {service['name']}[/]")
        console.print(f"     [{INK_LIGHT}]{service['description']}[/]")

        for agent in service["agents"]:
            console.print(f"     [{GREEN}]Agent:[/] {agent['name']} -- \"{agent['role']}\"")

            inputs = ", ".join(
                f"{f['name']} ({f['type']})" for f in agent["input_fields"]
            )
            outputs = ", ".join(
                f"{f['name']} ({f['type']})" for f in agent["output_fields"]
            )
            console.print(f"     [{INK_LIGHT}]Input:  {inputs}[/]")
            console.print(f"     [{INK_LIGHT}]Output: {outputs}[/]")

        if service.get("tools"):
            tool_names = ", ".join(t["name"] for t in service["tools"])
            console.print(f"     [{INK_LIGHT}]Tools:  {tool_names}[/]")

        console.print()

    # Pipeline
    pipeline_names = [step["service"] for step in plan["pipeline"]]
    pipeline_str = " -> ".join(pipeline_names)
    console.print(f"  [{GOLD}]Pipeline:[/] [{INK_LIGHT}]{pipeline_str}[/]")
    console.print()

    # Footer
    template_label = "Django webapp with dashboard" if template_name == "webapp" else "FastAPI API"
    console.print(f"  [{INK_LIGHT}]Template: {template_label}[/]")
    console.print(f"  [{INK_LIGHT}]SDK: OpenAI Agents SDK[/]")
    console.print()


def _update_registry_bulk(
    project_dir: Path,
    services: list[dict],
    sdk: str | None = None,
) -> None:
    """Register all services in registry/agents.json at once."""
    registry_path = project_dir / "registry" / "agents.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    for svc in services:
        slug = _normalize_name(svc["name"])
        service_entry = {
            "name": svc["name"],
            "slug": slug,
            "path": f"services/{slug}",
            "registeredAt": datetime.now(timezone.utc).isoformat(),
            "lastRun": None,
            "status": "registered",
            "agents": [
                {"name": a["name"], "role": a["role"]}
                for a in svc["agents"]
            ],
        }
        if sdk:
            service_entry["sdk"] = sdk
        registry["services"].append(service_entry)

    registry["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def _create_services(project_dir: Path, plan: dict, tree) -> None:
    """Generate all service directories and files from the LLM plan."""
    from covenant_cli.generators import (
        generate_schemas_file,
        generate_agent_file,
        generate_tools_file,
        generate_manager_file,
        generate_service_init,
        generate_agents_init,
        generate_schemas_init,
        _normalize_name as gen_normalize,
    )

    # Build pipeline lookup: service name -> pipeline step
    pipeline_lookup = {}
    for step in plan.get("pipeline", []):
        pipeline_lookup[step["service"]] = step

    for svc in plan["services"]:
        slug = _normalize_name(svc["name"])
        svc_dir = project_dir / "services" / slug

        # Create directory structure
        (svc_dir / "agents").mkdir(parents=True, exist_ok=True)
        (svc_dir / "schemas").mkdir(parents=True, exist_ok=True)
        (svc_dir / "memory").mkdir(parents=True, exist_ok=True)

        # __init__.py
        content = generate_service_init(svc)
        (svc_dir / "__init__.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/__init__.py"))

        # schemas/__init__.py
        content = generate_schemas_init(svc)
        (svc_dir / "schemas" / "__init__.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/schemas/__init__.py"))

        # schemas/types.py
        content = generate_schemas_file(svc)
        (svc_dir / "schemas" / "types.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/schemas/types.py"))

        # agents/__init__.py
        content = generate_agents_init(svc)
        (svc_dir / "agents" / "__init__.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/agents/__init__.py"))

        # Individual agent files
        for agent in svc["agents"]:
            content = generate_agent_file(agent, svc)
            (svc_dir / "agents" / f"{agent['name']}.py").write_text(
                content, encoding="utf-8"
            )
            tree.add(file_added(f"services/{slug}/agents/{agent['name']}.py"))

        # tools.py
        content = generate_tools_file(svc)
        (svc_dir / "tools.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/tools.py"))

        # manager.py
        pipeline_step = pipeline_lookup.get(
            svc["name"],
            {"step": "?", "input": "see pipeline config"},
        )
        content = generate_manager_file(svc, pipeline_step)
        (svc_dir / "manager.py").write_text(content, encoding="utf-8")
        tree.add(file_added(f"services/{slug}/manager.py"))

        # memory/README.md
        (svc_dir / "memory" / "README.md").write_text(
            f"# {svc['name']} Memory\n\n"
            "Service-specific exit reports and learnings.\n"
            "The manager writes here after every run.\n",
            encoding="utf-8",
        )
        tree.add(file_added(f"services/{slug}/memory/README.md"))


@click.command()
@click.argument("description")
@click.option(
    "--sdk",
    type=click.Choice(["openai", "crewai", "langgraph"]),
    default="openai",
    help="Agent SDK to use (default: openai).",
)
@click.option(
    "--template",
    "template_name",
    type=click.Choice(["webapp", "api"]),
    default="webapp",
    help="Application template: webapp (Django) or api (FastAPI).",
)
def create_command(description: str, sdk: str, template_name: str):
    """Create a governed app from a description.

    DESCRIPTION is a natural language description of what you want to build.

    Example:
        covenant create "A research app that searches papers and writes reviews"
    """
    # 1. Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print_error(
            "Set OPENAI_API_KEY to use covenant create.\n"
            "  export OPENAI_API_KEY=sk-..."
        )
        raise SystemExit(1)

    # 2. Call LLM with spinner
    console.print()
    try:
        with console.status(
            f"[{GOLD}]Interpreting your request...[/]",
            spinner="dots",
        ):
            from covenant_cli.llm import generate_plan
            plan = generate_plan(description)
    except ImportError as e:
        print_error(str(e))
        raise SystemExit(1)
    except EnvironmentError as e:
        print_error(str(e))
        raise SystemExit(1)
    except ValueError as e:
        print_error(
            f"Could not generate a valid plan after 2 attempts.\n"
            f"  {e}\n\n"
            f"Try a more specific description."
        )
        raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise SystemExit(1)

    # 3. Warn if too many services
    if len(plan["services"]) > 5:
        console.print(
            f"  [{OXBLOOD}]Plan has {len(plan['services'])} services. "
            f"Covenant recommends 5 or fewer.[/]"
        )
        if not click.confirm("  Proceed anyway?", default=False):
            console.print(f"  [{INK_LIGHT}]Plan rejected.[/]")
            raise SystemExit(0)

    # 4. Display plan
    _display_plan(plan, template_name)

    # 5. Confirm
    proceed = click.confirm("  Proceed?", default=False)
    if not proceed:
        console.print()
        console.print(
            f"  [{INK_LIGHT}]Plan rejected. "
            f"Re-run with a different description.[/]"
        )
        raise SystemExit(0)

    # 6. Create project
    project_name = plan["project_name"]
    project_dir = Path.cwd() / project_name

    if project_dir.exists() and any(project_dir.iterdir()):
        print_error(f"Directory '{project_name}' already exists and is not empty.")
        raise SystemExit(1)

    project_dir.mkdir(parents=True, exist_ok=True)

    # Prepare context for template init
    context = {
        "project_name": project_name,
        "project_slug": project_name.replace("-", "_").replace(" ", "_").lower(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sdk": sdk,
    }

    tree = branded_tree(f"{project_name}/")

    # 7. Create the app shell
    from covenant_cli.commands.init_project import (
        _init_webapp,
        _init_api,
        _create_governance_scaffold,
    )

    if template_name == "webapp":
        missing = _init_webapp(project_dir, context, tree, sdk)
    else:
        missing = _init_api(project_dir, context, tree, sdk)

    # 8. Generate services from plan
    _create_services(project_dir, plan, tree)

    # 9. Update registry with all services
    _update_registry_bulk(project_dir, plan["services"], sdk=sdk)

    # 10. Display results
    console.print()
    console.print(tree)
    console.print()

    if missing:
        for mf in missing:
            rel = mf.relative_to(project_dir)
            console.print(f"  [{OXBLOOD}]![/] [{INK_LIGHT}]Failed to create: {rel}[/]")
        console.print()

    svc_count = len(plan["services"])
    agent_count = sum(len(s["agents"]) for s in plan["services"])

    console.print(
        branded_panel(
            f"[bold {GOLD}]Project '{project_name}' created with "
            f"{svc_count} services and {agent_count} agents.[/]\n\n"
            f"  [{INK_LIGHT}]cd {project_name}[/]\n"
            f"  [{INK_LIGHT}]pip install -r requirements.txt[/]\n"
            + (
                f"  [{INK_LIGHT}]python manage.py migrate[/]\n"
                f"  [{INK_LIGHT}]python manage.py runserver[/]\n"
                if template_name == "webapp"
                else f"  [{INK_LIGHT}]uvicorn main:app --reload[/]\n"
            )
            + f"\n"
            f"  [{INK_LIGHT}]Each service has TODO stubs in tools.py -- implement them.[/]\n"
            f"  [{INK_LIGHT}]Agent instructions and types are ready to use.[/]\n\n"
            f"Read [bold]GOVERNANCE.md[/] [{INK_LIGHT}]-- it's the law.[/]",
            title="Next Steps",
        )
    )
