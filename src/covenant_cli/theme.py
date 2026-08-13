"""Covenant CLI -- shared brand theme.

Visual identity for the Covenant Foundation CLI.
All commands import from here for consistent styling.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree


# ── Brand Colors (Rich-compatible hex) ────────────────────────────────

GOLD = "#b48a2a"
GOLD_DIM = "#8a6a1f"
INK_DEEP = "#181410"
INK_MID = "#3a322a"
INK = "#6f6457"
INK_LIGHT = "#9a8e7c"
PAPER = "#f3ecd8"
OXBLOOD = "#6b2a2a"
NIGHT = "#14110d"
GREEN = "#6b8a3a"


# ── Semantic Styles ───────────────────────────────────────────────────

STYLE_HEADING = f"bold {GOLD}"
STYLE_ACCENT = GOLD
STYLE_DIM = INK_LIGHT
STYLE_ERROR = OXBLOOD
STYLE_SUCCESS = GOLD
STYLE_FILE_ADD = GREEN
STYLE_SECONDARY = INK


# ── The Banner ────────────────────────────────────────────────────────

BANNER = """\
  [bold #b48a2a]  .o.     .o.
   o   'o.o'   o
    'o'     'o'

   C O V E N A N T[/bold #b48a2a]

  [#9a8e7c]Governed agents.
   From the first line.[/]"""


BANNER_PLAIN = """\
    .o.     .o.
   o   'o.o'   o
    'o'     'o'

   C O V E N A N T

   Governed agents.
   From the first line."""


# ── Shared Console ────────────────────────────────────────────────────

console = Console()


# ── Helper Functions ──────────────────────────────────────────────────

def print_banner() -> None:
    """Print the branded banner inside a gold-bordered panel."""
    console.print()
    console.print(
        Panel(
            BANNER,
            border_style=GOLD_DIM,
            expand=False,
            padding=(1, 3),
        )
    )


def branded_panel(
    content: str,
    title: str | None = None,
    expand: bool = False,
) -> Panel:
    """Create a panel with gold border and branded title style."""
    return Panel(
        content,
        title=f"[{GOLD}]{title}[/]" if title else None,
        border_style=GOLD_DIM,
        expand=expand,
        padding=(1, 2),
    )


def branded_table(
    title: str,
    columns: list[tuple[str, str]],
    show_lines: bool = True,
) -> Table:
    """Create a table with gold header styling.

    columns: list of (name, style) tuples.
    """
    table = Table(
        title=f"[{GOLD}]{title}[/]",
        show_lines=show_lines,
        border_style=INK,
        header_style=f"bold {GOLD}",
    )
    for col_name, col_style in columns:
        table.add_column(col_name, style=col_style)
    return table


def branded_tree(label: str) -> Tree:
    """Create a tree with gold root label."""
    return Tree(f"[{STYLE_HEADING}]{label}[/]")


def file_added(filename: str) -> str:
    """Format a file-added line for tree display."""
    return f"[{GREEN}]+[/] [{INK_LIGHT}]{filename}[/]"


def print_error(message: str) -> None:
    """Print an error message in oxblood."""
    console.print(f"[{OXBLOOD}]{message}[/]")


def print_success(message: str) -> None:
    """Print a success message in gold."""
    console.print(f"[bold {GOLD}]{message}[/]")


def print_dim(message: str) -> None:
    """Print secondary/muted text."""
    console.print(f"[{INK_LIGHT}]{message}[/]")
