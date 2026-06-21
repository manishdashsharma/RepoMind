from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "primary": "bold cyan",
        "secondary": "bold blue",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim white",
        "muted": "dim",
        "brand": "bold bright_cyan",
        "agent": "bold magenta",
        "highlight": "bold white on blue",
        "code": "bright_white on grey23",
    }
)

console = Console(theme=THEME, highlight=False)
err_console = Console(stderr=True, theme=THEME)

_BANNER = r"""
 ██████╗ ███████╗██████╗  ██████╗ ███╗   ███╗██╗███╗   ██╗██████╗
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗████╗ ████║██║████╗  ██║██╔══██╗
 ██████╔╝█████╗  ██████╔╝██║   ██║██╔████╔██║██║██╔██╗ ██║██║  ██║
 ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██║╚██╔╝██║██║██║╚██╗██║██║  ██║
 ██║  ██║███████╗██║     ╚██████╔╝██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝
"""


def print_banner() -> None:
    console.print(Text(_BANNER, style="brand", justify="center"))
    console.print(
        Align.center(
            Text(
                "Ask your codebase anything — locally, privately, powerfully",
                style="info",
            )
        )
    )
    console.print(
        Align.center(Text("v0.1.4 · MIT · github.com/manishdashsharma/RepoMind", style="muted"))
    )
    console.print()


def success(message: str) -> None:
    console.print(f"[success]  ✓[/success]  {message}")


def error(message: str) -> None:
    console.print(f"[error]  ✗[/error]  {message}")


def warning(message: str) -> None:
    console.print(f"[warning]  ⚠[/warning]  {message}")


def info(message: str) -> None:
    console.print(f"[info]  →[/info]  {message}")


def section(title: str) -> None:
    console.print()
    console.rule(f"[primary] {title} [/primary]")
    console.print()


def panel(content: str, title: str = "", style: str = "primary") -> None:
    console.print(Panel(content, title=title, border_style=style, padding=(1, 2)))


@contextmanager
def spinner(message: str) -> Generator[None, None, None]:
    with console.status(f"[primary]{message}[/primary]", spinner="dots2"):
        yield


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(spinner_name="dots2", style="primary"),
        TextColumn("[primary]{task.description}[/primary]"),
        BarColumn(bar_width=38, complete_style="cyan", finished_style="green"),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def make_table(title: str, columns: list[tuple[str, str]]) -> Table:
    table = Table(
        title=title,
        box=box.ROUNDED,
        border_style="primary",
        header_style="bold cyan",
        show_lines=True,
        title_style="bold white",
        min_width=60,
    )
    for col_name, col_style in columns:
        table.add_column(col_name, style=col_style)
    return table
