from __future__ import annotations

from rich.console import Console

from tick.templates.registry import template_keys


def templates_command() -> None:
    console = Console()
    templates = template_keys()
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    console.print("[bold]Available templates:[/bold]")
    for name in templates:
        console.print(f"- {name}")
