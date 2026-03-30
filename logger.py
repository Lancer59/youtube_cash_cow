"""
logger.py
Centralized logger using 'rich' for beautiful colored terminal output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.theme import Theme

theme = Theme({
    "info":    "bold cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error":   "bold red",
    "step":    "bold magenta",
})

console = Console(theme=theme)


def banner():
    console.print(Panel.fit(
        "[bold yellow]🎬 YouTube Shorts Cash Cow[/bold yellow]\n[dim]History Niche · Fully Automated[/dim]",
        border_style="yellow"
    ))


def step(number: int, total: int, message: str):
    console.print(f"\n[step]▶ Step {number}/{total}[/step] [white]{message}[/white]")


def info(message: str):
    console.print(f"  [info]ℹ  {message}[/info]")


def success(message: str):
    console.print(f"  [success]✅ {message}[/success]")


def warning(message: str):
    console.print(f"  [warning]⚠  {message}[/warning]")


def error(message: str):
    console.print(f"  [error]❌ {message}[/error]")


def done(video_path: str):
    console.print(Panel.fit(
        f"[bold green]🎉 Pipeline Complete![/bold green]\n[dim]Video saved to:[/dim] [cyan]{video_path}[/cyan]",
        border_style="green"
    ))


def spinner(message: str):
    """Returns a rich Progress spinner context manager."""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]  {message}[/bold cyan]"),
        transient=True,
    )
