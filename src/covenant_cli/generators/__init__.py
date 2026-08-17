"""Code generators for covenant create.

Turns LLM plan dicts into Python source code strings.
Each function takes a service/agent spec and returns a complete .py file.
"""

import re


# --- Type Safety ---

SUPPORTED_TYPES = {
    "str", "int", "float", "bool",
    "list[str]", "list[int]", "list[float]",
    "dict[str, str]", "dict[str, Any]",
}

# Normalize common LLM type hallucinations
TYPE_ALIASES = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "number": "float",
    "array": "list[str]",
    "object": "dict[str, str]",
    "list": "list[str]",
    "dict": "dict[str, str]",
}


def _safe_type(ftype: str) -> str:
    """Normalize a type annotation to a supported Python type."""
    ftype = ftype.strip()
    if ftype in SUPPORTED_TYPES:
        return ftype
    if ftype.lower() in TYPE_ALIASES:
        return TYPE_ALIASES[ftype.lower()]
    # Try to match list[X] or dict[X, Y] patterns
    if ftype.startswith("list[") or ftype.startswith("dict["):
        return ftype  # Trust it if it looks structured
    if ftype.startswith("List["):
        return ftype.replace("List[", "list[", 1)
    if ftype.startswith("Dict["):
        return ftype.replace("Dict[", "dict[", 1)
    # Fallback to str for anything unrecognized
    return "str"


def _normalize_tool_param_type(param_type: str) -> str:
    """Normalize a tool parameter type string."""
    return _safe_type(param_type)


# --- Helpers ---

def _normalize_name(name: str) -> str:
    """Lowercase hyphenated to snake_case."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _to_class_name(name: str) -> str:
    """snake_case or hyphenated to PascalCase."""
    return "".join(
        word.capitalize()
        for word in re.split(r"[-_]+", name)
        if word
    )


def _python_literal(value: str, ftype: str) -> str:
    """Convert a string default to a Python literal based on type."""
    if ftype == "int":
        return value
    elif ftype == "float":
        return value
    elif ftype == "bool":
        return value.capitalize()
    elif ftype.startswith("list"):
        return "[]" if not value else value
    elif ftype.startswith("dict"):
        return "{}" if not value else value
    else:
        return f'"{value}"'


def _pydantic_field(field: dict) -> str:
    """Generate a Pydantic field line from a field spec."""
    ftype = _safe_type(field["type"])
    fname = field["name"]
    desc = field["description"].replace('"', '\\"')
    default = field.get("default")

    if default is not None:
        return f'    {fname}: {ftype} = Field(default={_python_literal(default, ftype)}, description="{desc}")'
    else:
        return f'    {fname}: {ftype} = Field(..., description="{desc}")'


def _escape_triple_quotes(text: str) -> str:
    """Escape triple quotes in text that will be placed inside triple-quoted strings."""
    return text.replace('"""', '\\"\\"\\"')


# --- Generators ---

def generate_schemas_file(service_spec: dict) -> str:
    """Generate Pydantic models for a service's agents."""
    lines = [
        f'"""Service types for {service_spec["name"]}."""',
        "",
        "from datetime import datetime",
        "from pydantic import BaseModel, Field",
        "",
        "",
    ]

    for agent in service_spec["agents"]:
        agent_class = _to_class_name(agent["name"])

        # Input model
        lines.append(f"class {agent_class}Input(BaseModel):")
        lines.append(f'    """Input for {agent["role"]}."""')
        for field in agent["input_fields"]:
            lines.append(_pydantic_field(field))
        lines.append("")
        lines.append("")

        # Output model — flatten complex types (dict, nested) to str
        # for reliable LLM JSON parsing
        lines.append(f"class {agent_class}Output(BaseModel):")
        lines.append(f'    """Output from {agent["role"]}."""')
        for field in agent["output_fields"]:
            simplified = dict(field)
            ftype = simplified.get("type", "str")
            if "dict" in ftype.lower():
                simplified["type"] = "str"
            lines.append(_pydantic_field(simplified))
        lines.append("")
        lines.append("")

    # Standard governance types
    lines.extend([
        "class UsageStats(BaseModel):",
        '    """Token usage statistics for a service run."""',
        '    input_tokens: int = Field(default=0, description="Total input tokens consumed")',
        '    output_tokens: int = Field(default=0, description="Total output tokens consumed")',
        '    total_cost: float = Field(default=0.0, description="Total cost in USD")',
        "",
        "",
        "class ExitReport(BaseModel):",
        '    """Structured exit report for memory/inheritance/."""',
        "    service: str",
        "    timestamp: datetime",
        "    duration_seconds: float",
        "    status: str",
        "    what_worked: list[str] = []",
        "    what_failed: list[str] = []",
        "    recommendations: list[str] = []",
        "    usage: UsageStats = Field(default_factory=UsageStats)",
        "",
    ])

    return "\n".join(lines)


def generate_agent_file(agent_spec: dict, service_spec: dict) -> str:
    """Generate an Agent definition file."""
    slug = _normalize_name(service_spec["name"])
    agent_class = _to_class_name(agent_spec["name"])
    instructions = _escape_triple_quotes(agent_spec["instructions"])

    # Build tool import list
    tool_imports = ""
    tool_list = ""
    if service_spec.get("tools"):
        tool_names = [t["name"] for t in service_spec["tools"]]
        tool_imports = f"from ..tools import {', '.join(tool_names)}"
        tool_list = f"    tools=[{', '.join(tool_names)}],"

    lines = [
        f'"""{service_spec["name"]} -- {agent_spec["role"]}.',
        "",
        "Governance rules:",
        "  - Rule 2: Typed I/O (Pydantic models for input/output)",
        "  - Rule 3: One agent per file",
        "  - Rule 6: Distill, don't dump (instructions are focused)",
        '"""',
        "",
        "from agents import Agent",
    ]

    if tool_imports:
        lines.append(tool_imports)

    lines.extend([
        "",
        "",
        f'INSTRUCTIONS = """{instructions}"""',
        "",
        "",
        f"{agent_spec['name']} = Agent(",
        f'    name="{slug}_{agent_spec["name"]}",',
        f"    instructions=INSTRUCTIONS,",
        f'    model="gpt-4o-mini",',
    ])

    if tool_list:
        lines.append(tool_list)

    lines.extend([
        ")",
        "",
    ])

    return "\n".join(lines)


def generate_tools_file(
    service_spec: dict,
    implementations: dict[str, str] | None = None,
) -> str:
    """Generate tool functions for a service.

    When ``implementations`` is provided and contains a key matching a tool
    name, the LLM-generated implementation is used instead of a stub.
    """
    tools = service_spec.get("tools", [])

    lines = [
        f'"""{service_spec["name"]} -- tools."""',
        "",
    ]

    if not tools:
        lines.append("# No tools defined for this service.")
        lines.append("# Add tools here and import them in your agent files.")
        lines.append("")
        return "\n".join(lines)

    lines.extend([
        "from agents import function_tool",
        "",
        "",
    ])

    for tool in tools:
        tool_name = tool["name"]

        # Check if we have a generated implementation for this tool
        if implementations and tool_name in implementations:
            impl_code = implementations[tool_name]
            lines.append("# GENERATED -- review before production")
            lines.append("@function_tool")
            # The implementation already contains the full function def
            # with imports prepended. We need to extract imports and the
            # function body separately.
            impl_lines = impl_code.split("\n")
            import_lines = []
            func_lines = []
            in_func = False
            for line in impl_lines:
                if line.startswith("def "):
                    in_func = True
                if in_func:
                    func_lines.append(line)
                elif line.strip() and not line.strip().startswith("#"):
                    # Import line -- only add if not already present
                    if line.strip().startswith(("import ", "from ")):
                        import_lines.append(line)
                elif line.strip().startswith("# requires:"):
                    # Keep requires comments
                    import_lines.append(line)

            # Insert imports near the top (after the module-level imports)
            # We insert them just before the function_tool import
            if import_lines:
                # Add imports after the existing "from agents ..." line
                for imp in import_lines:
                    if imp not in lines:
                        lines.insert(lines.index("from agents import function_tool") + 1, imp)

            if func_lines:
                lines.extend(func_lines)
            else:
                # Fallback: dump the whole implementation after decorator
                lines.extend(impl_lines)
            lines.extend(["", ""])
        else:
            # Stub fallback
            normalized_params = []
            for param in tool["params"]:
                if ": " in param:
                    pname, ptype = param.split(": ", 1)
                    ptype = _normalize_tool_param_type(ptype)
                    normalized_params.append(f"{pname}: {ptype}")
                else:
                    normalized_params.append(param)
            param_str = ", ".join(normalized_params)
            desc = tool["description"].replace('"', '\\"')
            lines.extend([
                "@function_tool",
                f"def {tool_name}({param_str}) -> str:",
                f'    """{desc}"""',
                f"    # TODO: Implement {tool_name}",
                f'    return "TODO: {tool_name} is not yet implemented. Edit services/<slug>/tools.py to add the implementation."',
                "",
                "",
            ])

    return "\n".join(lines)


def extract_required_packages(implementations: dict[str, str]) -> list[str]:
    """Extract ``# requires: <package>`` comments from generated code.

    Returns a deduplicated list of package names.
    """
    packages: list[str] = []
    for code in implementations.values():
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# requires:"):
                pkg = stripped.split("# requires:", 1)[1].strip()
                if pkg and pkg not in packages:
                    packages.append(pkg)
    return packages


def generate_manager_file(service_spec: dict, pipeline_step: dict) -> str:
    """Generate a service manager with pipeline orchestration."""
    slug = _normalize_name(service_spec["name"])
    service_class = _to_class_name(slug)

    # Build agent imports
    agent_imports = []
    agent_runs = []
    for agent in service_spec["agents"]:
        agent_imports.append(
            f"from .agents.{agent['name']} import {agent['name']}"
        )
        agent_runs.append(
            f'            # Build pipeline-aware input\n'
            f'            input_parts = []\n'
            f'            if request.get("query"):\n'
            f'                input_parts.append(f"User request: {{request[\'query\']}}")\n'
            f'            for key, val in request.items():\n'
            f'                if key.endswith("_output") and val:\n'
            f'                    input_parts.append(f"Previous agent output: {{val}}")\n'
            f'            if request.get("previous_result"):\n'
            f'                input_parts.append(f"Upstream result: {{request[\'previous_result\']}}")\n'
            f'            input_text = "\\n\\n".join(input_parts) if input_parts else str(request)\n'
            f'\n'
            f'            agent_result = await Runner.run(\n'
            f'                {agent["name"]},\n'
            f'                input=input_text,\n'
            f'            )\n'
            f'            # Serialize Pydantic output for JSON compatibility\n'
            f'            output = agent_result.final_output\n'
            f'            if hasattr(output, "model_dump"):\n'
            f'                output = output.model_dump()\n'
            f'            result["{agent["name"]}_output"] = output\n'
            f'            what_worked.append("{agent["name"]} completed")'
        )

    agent_imports_str = "\n".join(agent_imports)
    agent_runs_str = "\n\n".join(agent_runs)

    return f'''"""{service_spec["name"]} -- service manager (OpenAI Agents SDK).

The manager orchestrates agents sequentially and writes exit reports.
See GOVERNANCE.md rules 4 (manager orchestration) and 5 (exit reports).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import Runner

{agent_imports_str}


class {service_class}Manager:
    """Orchestrator for the {service_spec["name"]} service.

    Pipeline step {pipeline_step["step"]}: {pipeline_step["input"]}
    """

    def __init__(self):
        self.service_name = "{slug}"
        self.memory_dir = Path("memory/inheritance")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._usage = {{"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}}

    def track_usage(self, input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0):
        """Track token usage for this run."""
        self._usage["input_tokens"] += input_tokens
        self._usage["output_tokens"] += output_tokens
        self._usage["total_cost"] += cost

    async def run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run the service pipeline."""
        if not os.environ.get("OPENAI_API_KEY"):
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Add your key to .env"
            )
        start_time = datetime.now(timezone.utc)
        what_worked: list[str] = []
        what_failed: list[str] = []
        result: dict[str, Any] = {{}}

        try:
            inheritance = self._read_inheritance()
            if inheritance:
                what_worked.append(f"Read {{len(inheritance)}} prior exit reports")

{agent_runs_str}

            result["status"] = "completed"
            what_worked.append("Pipeline completed")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            what_failed.append(f"Pipeline failed: {{e}}")

        self._write_exit_report(result, start_time, what_worked, what_failed)
        return result

    def _read_inheritance(self) -> list[dict]:
        """Read prior exit reports. Governance rule 7."""
        reports = []
        for path in sorted(self.memory_dir.glob(f"{{self.service_name}}-*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                reports.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return reports

    def _write_exit_report(self, result, start_time, what_worked, what_failed):
        """Write exit report. Governance rule 5."""
        now = datetime.now(timezone.utc)
        duration = (now - start_time).total_seconds()
        report = {{
            "service": self.service_name,
            "timestamp": now.isoformat(),
            "duration_seconds": round(duration, 2),
            "status": result.get("status", "unknown"),
            "what_worked": what_worked,
            "what_failed": what_failed,
            "recommendations": [],
            "usage": self._usage,
        }}
        filename = f"{{self.service_name}}-{{now.strftime(\'%Y%m%dT%H%M%S\')}}.json"
        (self.memory_dir / filename).write_text(
            json.dumps(report, indent=2) + "\\n", encoding="utf-8"
        )
'''


def generate_service_init(service_spec: dict) -> str:
    """Generate the service __init__.py that exports the Manager."""
    slug = _normalize_name(service_spec["name"])
    service_class = _to_class_name(slug)
    return (
        f'"""{service_spec["name"]} -- governed agent service."""\n\n'
        f'from .manager import {service_class}Manager\n\n'
        f'__all__ = ["{service_class}Manager"]\n'
    )


def generate_agents_init(service_spec: dict) -> str:
    """Generate the agents/ __init__.py that imports all agents."""
    slug = _normalize_name(service_spec["name"])
    lines = [f'"""Agents for the {slug} service."""', ""]
    for agent in service_spec["agents"]:
        lines.append(f"from .{agent['name']} import {agent['name']}")
    lines.append("")
    return "\n".join(lines)


def generate_schemas_init(service_spec: dict) -> str:
    """Generate the schemas/ __init__.py."""
    slug = _normalize_name(service_spec["name"])
    return f'"""Schemas for the {slug} service."""\n'


def generate_setup_script(project_name: str, sdk: str) -> str:
    """Generate setup.py (cross-platform setup script, not a package setup)."""
    return f'''#!/usr/bin/env python3
"""Setup script for {project_name}. Cross-platform (Windows, Mac, Linux)."""

import os
import subprocess
import sys
from pathlib import Path


def run(cmd, check=True):
    """Run a command and print it."""
    print(f"  $ {{' '.join(cmd) if isinstance(cmd, list) else cmd}}")
    subprocess.run(cmd, check=check, shell=isinstance(cmd, str))


def main():
    print()
    print(f"  Setting up {project_name}...")
    print()

    # Create virtual environment if not in one
    if not os.environ.get("VIRTUAL_ENV"):
        venv_dir = Path(".venv")
        if not venv_dir.exists():
            print("  Creating virtual environment...")
            run([sys.executable, "-m", "venv", ".venv"])
            print("  Virtual environment created.")
            print()
            # Tell user to activate and re-run
            if sys.platform == "win32":
                activate = ".venv\\\\Scripts\\\\activate"
            else:
                activate = "source .venv/bin/activate"
            print(f"  Activate it and re-run setup:")
            print(f"    {{activate}}")
            print(f"    python setup_project.py")
            return
        else:
            print("  .venv exists but is not activated.")
            if sys.platform == "win32":
                print("  Run: .venv\\\\Scripts\\\\activate")
            else:
                print("  Run: source .venv/bin/activate")
            print("  Then re-run: python setup_project.py")
            return

    # Install dependencies
    print("  Installing dependencies...")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print()

    # Set up .env file (Gap 3: API key handling)
    env_path = Path(".env")
    env_example = Path(".env.example")
    if not env_path.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_path)
        print("  Created .env from .env.example")
        print()

    # Check/prompt for API key
    from dotenv import load_dotenv
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        print("  Your agents need an OpenAI API key to run.")
        print("  Get one at: https://platform.openai.com/api-keys")
        print()
        key = input("  Paste your OpenAI API key (or press Enter to skip): ").strip()
        if key:
            env_content = env_path.read_text(encoding="utf-8")
            env_content = env_content.replace(
                "OPENAI_API_KEY=sk-your-key-here",
                f"OPENAI_API_KEY={{key}}",
            )
            env_path.write_text(env_content, encoding="utf-8")
            os.environ["OPENAI_API_KEY"] = key
            print("  API key saved to .env")
        else:
            print("  Skipped. Add your key to .env before running agents.")
        print()

    # Create and run Django migrations
    print("  Creating database migrations...")
    run([sys.executable, "manage.py", "makemigrations", "core"])
    print()
    print("  Applying migrations...")
    run([sys.executable, "manage.py", "migrate"])
    print()

    # Register services from registry/agents.json into Django (Gap 1)
    agents_json = Path("registry/agents.json")
    if agents_json.exists():
        print("  Registering services in Django...")
        run([sys.executable, "-c", """
import os, json, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import Service
registry = json.loads(open('registry/agents.json', encoding='utf-8').read())
services = registry.get('services', [])
for i, svc in enumerate(services):
    Service.objects.get_or_create(
        slug=svc['slug'],
        defaults={{
            'name': svc['name'],
            'sdk': svc.get('sdk', 'openai'),
            'status': 'registered',
            'description': svc.get('description', ''),
            'order': i,
        }}
    )
print(f"  Registered {{len(services)}} services.")
"""])
        print()
    else:
        print("  No registry/agents.json found -- skipping service registration.")
        print()

    # Optional superuser creation (Gap 5)
    print("  Create admin superuser? (optional, for /admin/ access)")
    create_su = input("  Create superuser? [y/N]: ").strip().lower()
    if create_su == "y":
        run([sys.executable, "manage.py", "createsuperuser"])
    print()

    print("  Setup complete! Next steps:")
    print(f"    python manage.py runserver")
    print(f"    Then visit http://127.0.0.1:8000/")
    print()


if __name__ == "__main__":
    main()
'''


def generate_pipeline_runner(plan: dict) -> str:
    """Generate run_pipeline.py that executes the full service pipeline."""
    project_name = plan["project_name"]
    services = plan["services"]
    pipeline = plan.get("pipeline", [])

    # Build pipeline order: list of (slug, class_name) tuples
    pipeline_steps = []
    for step in pipeline:
        slug = _normalize_name(step["service"])
        class_name = _to_class_name(slug)
        pipeline_steps.append((slug, class_name, step.get("input", "")))

    # If no pipeline defined, fall back to service order
    if not pipeline_steps:
        for svc in services:
            slug = _normalize_name(svc["name"])
            class_name = _to_class_name(slug)
            pipeline_steps.append((slug, class_name, ""))

    total = len(pipeline_steps)
    pipeline_arrow = " -> ".join(s[0] for s in pipeline_steps)

    # Build import lines
    import_lines = []
    for slug, class_name, _ in pipeline_steps:
        import_lines.append(
            f"from services.{slug}.manager import {class_name}Manager"
        )
    imports_str = "\n".join(import_lines)

    # Build run steps
    step_blocks = []
    for i, (slug, class_name, input_desc) in enumerate(pipeline_steps, 1):
        var_name = f"result{i}"
        prev_var = f"result{i - 1}" if i > 1 else None

        if i == 1:
            input_expr = '{"query": user_input}'
        else:
            input_expr = prev_var

        block = (
            f'    # Step {i}: {slug}\n'
            f'    print("  [{i}/{total}] Running {slug}...")\n'
            f'    manager{i} = {class_name}Manager()\n'
            f'    {var_name} = await manager{i}.run({input_expr})\n'
            f'    print(f"       Status: {{{var_name}.get(\'status\', \'unknown\')}}")\n'
        )
        step_blocks.append(block)

    steps_str = "\n".join(step_blocks)
    final_var = f"result{total}"

    return f'''#!/usr/bin/env python3
"""Run the {project_name} agent pipeline end-to-end.

Usage:
    python run_pipeline.py "your input text here"
    python run_pipeline.py --dry-run  (show pipeline without running)
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

{imports_str}


async def run_pipeline(user_input: str) -> dict:
    """Execute the full pipeline sequentially."""
    print(f"\\n  Pipeline: {pipeline_arrow}")
    print(f"  Input: {{user_input[:80]}}...")
    print()

{steps_str}
    print("\\n  Pipeline complete.")
    print("  Exit reports written to memory/inheritance/")
    return {final_var}


def main():
    if "--dry-run" in sys.argv:
        print("\\n  DRY RUN -- Pipeline structure:")
        print("  {pipeline_arrow}")
        print("  No agents executed.")
        return

    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py \\"your input text\\"")
        print("       python run_pipeline.py --dry-run")
        sys.exit(1)

    user_input = sys.argv[1]
    result = asyncio.run(run_pipeline(user_input))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
'''
