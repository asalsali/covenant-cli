"""Convention rules for IDE integration."""

from pathlib import Path

RULES_DIR = Path(__file__).parent


def get_rules_dir() -> Path:
    """Return the path to convention rule files."""
    return RULES_DIR
