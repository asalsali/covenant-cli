"""LLM integration for covenant create.

Calls OpenAI API to generate a structured plan from a natural language
description. Handles retries, validation, and error reporting.
"""

import json
import os

from .prompts import SYSTEM_PROMPT


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
