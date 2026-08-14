"""LLM integration for covenant create.

Calls OpenAI API to generate a structured plan from a natural language
description. Handles retries, validation, and error reporting.
Also generates working tool implementations via a second LLM call.
"""

import json
import os
import re

from .prompts import SYSTEM_PROMPT, TOOL_IMPLEMENTATION_PROMPT


# --- Validation ---

REQUIRED_TOP_KEYS = {"project_name", "services", "pipeline"}
REQUIRED_SERVICE_KEYS = {"name", "agents"}
REQUIRED_AGENT_KEYS = {"name", "role", "instructions", "input_fields", "output_fields"}
REQUIRED_FIELD_KEYS = {"name", "type", "description"}


def validate_plan(plan: dict) -> list[str]:
    """Return list of missing field descriptions, empty if valid."""
    errors = []
    for key in REQUIRED_TOP_KEYS:
        if key not in plan:
            errors.append(f"top-level.{key}")

    for i, svc in enumerate(plan.get("services", [])):
        for key in REQUIRED_SERVICE_KEYS:
            if key not in svc:
                errors.append(f"services[{i}].{key}")
        for j, agent in enumerate(svc.get("agents", [])):
            for key in REQUIRED_AGENT_KEYS:
                if key not in agent:
                    errors.append(f"services[{i}].agents[{j}].{key}")
            for k, field in enumerate(agent.get("input_fields", [])):
                for key in REQUIRED_FIELD_KEYS:
                    if key not in field:
                        errors.append(
                            f"services[{i}].agents[{j}].input_fields[{k}].{key}"
                        )
            for k, field in enumerate(agent.get("output_fields", [])):
                for key in REQUIRED_FIELD_KEYS:
                    if key not in field:
                        errors.append(
                            f"services[{i}].agents[{j}].output_fields[{k}].{key}"
                        )

    return errors


def _validate_plan_strict(plan: dict) -> None:
    """Validate the LLM plan has required fields. Raises on failure."""
    required = ["project_name", "project_description", "services", "pipeline"]
    for key in required:
        if key not in plan:
            raise ValueError(f"Plan missing required field: {key}")
    if not plan["services"]:
        raise ValueError("Plan has no services")
    for svc in plan["services"]:
        if not svc.get("agents"):
            raise ValueError(f"Service '{svc.get('name', '?')}' has no agents")


# --- LLM Call ---

def generate_plan(description: str) -> dict:
    """Call OpenAI to interpret a user request into a structured plan.

    Retries once on parse or validation failure.
    Raises EnvironmentError if OPENAI_API_KEY is not set.
    Raises SystemExit on unrecoverable errors.
    """
    # Lazy import -- the openai package should only be required for create
    try:
        from openai import OpenAI, APIConnectionError, RateLimitError
    except ImportError:
        raise ImportError(
            "The 'openai' package is required for covenant create.\n"
            "  pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    user_prompt = description
    last_error = None

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content
            plan = json.loads(raw)

            # Validate schema
            errors = validate_plan(plan)
            if errors:
                if attempt == 0:
                    user_prompt = (
                        f"{description}\n\n"
                        f"IMPORTANT: Your previous response was missing these fields: "
                        f"{', '.join(errors)}. Include ALL required fields."
                    )
                    last_error = f"Missing fields: {', '.join(errors)}"
                    continue
                raise ValueError(f"Plan missing fields after retry: {', '.join(errors)}")

            _validate_plan_strict(plan)

            # Ensure project_description exists (non-required in schema check but nice to have)
            if "project_description" not in plan:
                plan["project_description"] = description

            return plan

        except json.JSONDecodeError as e:
            if attempt == 0:
                user_prompt = (
                    f"{description}\n\n"
                    "IMPORTANT: Return ONLY valid JSON, no other text."
                )
                last_error = f"Invalid JSON: {e}"
                continue
            raise ValueError(f"Could not parse plan as JSON after retry: {e}")

        except APIConnectionError:
            raise SystemExit(
                "Could not reach OpenAI API. Check your internet connection."
            )

        except RateLimitError:
            raise SystemExit(
                "OpenAI rate limit hit. Wait a moment and try again."
            )

    # Should not reach here, but just in case
    raise ValueError(f"Failed to generate plan after 2 attempts. Last error: {last_error}")


# --- Tool Implementation Generation ---

def _build_tool_spec_prompt(tools: list[dict]) -> str:
    """Build the user prompt listing all tool specs for implementation."""
    lines = ["Generate implementations for these tools:", ""]
    for tool in tools:
        params_str = ", ".join(tool.get("params", []))
        lines.append(f"- {tool['name']}({params_str}): {tool['description']}")
    return "\n".join(lines)


def _parse_tool_implementations(raw_code: str, tool_names: list[str]) -> dict[str, str]:
    """Parse LLM output into a dict of tool_name -> implementation code.

    The LLM is instructed to separate tools with:
        # --- TOOL: tool_name ---
    """
    implementations: dict[str, str] = {}

    # Split on the tool separator pattern
    sections = re.split(r"# --- TOOL:\s*(\w+)\s*---", raw_code)

    # sections[0] = imports/preamble (before first separator)
    # sections[1] = first tool name, sections[2] = first tool code, etc.
    preamble = sections[0].strip() if sections else ""

    for i in range(1, len(sections) - 1, 2):
        tool_name = sections[i].strip()
        tool_code = sections[i + 1].strip()
        if tool_name in tool_names:
            # Prepend imports/preamble to each tool so it's self-contained
            if preamble:
                implementations[tool_name] = preamble + "\n\n" + tool_code
            else:
                implementations[tool_name] = tool_code

    return implementations


def generate_tool_implementations(tools: list[dict]) -> dict[str, str]:
    """Call LLM to generate working implementations for each tool.

    Args:
        tools: list of tool specs from the plan [{name, description, params}]

    Returns:
        dict mapping tool_name -> implementation code string.
        Falls back to empty dict on any failure.
    """
    if not tools:
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        return {}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {}

    client = OpenAI(api_key=api_key)
    tool_names = [t["name"] for t in tools]
    user_prompt = _build_tool_spec_prompt(tools)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": TOOL_IMPLEMENTATION_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_code = response.choices[0].message.content or ""

        # Strip markdown fences if the LLM included them despite instructions
        raw_code = re.sub(r"^```(?:python)?\s*\n?", "", raw_code.strip())
        raw_code = re.sub(r"\n?```\s*$", "", raw_code.strip())

        implementations = _parse_tool_implementations(raw_code, tool_names)

        return implementations

    except Exception:
        # Any failure -> fall back to stubs, never crash
        return {}
