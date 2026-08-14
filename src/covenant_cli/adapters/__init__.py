"""SDK adapter registry.

Maps supported SDK names to their package info, environment variables,
and display labels. Used by `covenant init --sdk` and `covenant add-service --sdk`
to select the right templates and dependencies.
"""

SUPPORTED_SDKS = {
    "openai": {
        "package": "openai-agents",
        "min_version": "0.5",
        "env_var": "OPENAI_API_KEY",
        "label": "OpenAI Agents SDK",
    },
    "crewai": {
        "package": "crewai",
        "min_version": "0.100",
        "env_var": "OPENAI_API_KEY",
        "label": "CrewAI",
    },
    "langgraph": {
        "package": "langgraph",
        "min_version": "0.3",
        "env_var": "OPENAI_API_KEY",
        "label": "LangGraph",
        "extra_packages": [
            {"package": "langchain-openai", "min_version": "0.3"},
        ],
    },
}


def get_sdk_info(sdk_name: str) -> dict | None:
    """Return SDK metadata dict, or None if unknown."""
    return SUPPORTED_SDKS.get(sdk_name)


def list_sdks() -> list[str]:
    """Return sorted list of supported SDK names."""
    return sorted(SUPPORTED_SDKS.keys())
