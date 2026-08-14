"""Jinja2 templates for project and service scaffolding."""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent


def get_project_template_dir() -> Path:
    """Return the path to project templates."""
    return TEMPLATE_DIR / "project"


def get_service_template_dir() -> Path:
    """Return the path to service templates."""
    return TEMPLATE_DIR / "service"


def get_api_template_dir() -> Path:
    """Return the path to API (FastAPI) templates."""
    return TEMPLATE_DIR / "api"


def get_webapp_template_dir() -> Path:
    """Return the path to webapp (Django) templates."""
    return TEMPLATE_DIR / "webapp"
