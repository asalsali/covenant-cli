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

        # Output model
        lines.append(f"class {agent_class}Output(BaseModel):")
        lines.append(f'    """Output from {agent["role"]}."""')
        for field in agent["output_fields"]:
            lines.append(_pydantic_field(field))
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
        f"from ..schemas.types import {agent_class}Input, {agent_class}Output",
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
        f"    output_type={agent_class}Output,",
    ])

    if tool_list:
        lines.append(tool_list)

    lines.extend([
        ")",
        "",
    ])

    return "\n".join(lines)


def generate_tools_file(service_spec: dict) -> str:
    """Generate tool function stubs for a service."""
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
        # Normalize parameter types
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
            f"def {tool['name']}({param_str}) -> str:",
            f'    """{desc}"""',
            f"    # TODO: Implement {tool['name']}",
            f'    raise NotImplementedError("{tool["name"]} is not yet implemented")',
            "",
            "",
        ])

    return "\n".join(lines)


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
            f'            agent_result = await Runner.run(\n'
            f'                {agent["name"]},\n'
            f'                input=request.get("query", ""),\n'
            f'            )\n'
            f'            result["{agent["name"]}_output"] = agent_result.final_output\n'
            f'            what_worked.append("{agent["name"]} completed")'
        )

    agent_imports_str = "\n".join(agent_imports)
    agent_runs_str = "\n\n".join(agent_runs)

    return f'''"""{service_spec["name"]} -- service manager (OpenAI Agents SDK).

The manager orchestrates agents sequentially and writes exit reports.
See GOVERNANCE.md rules 4 (manager orchestration) and 5 (exit reports).
"""

import json
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
