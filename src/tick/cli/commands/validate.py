from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader


def validate_command(checklist: Path) -> None:
    console = Console()
    loader = YamlChecklistLoader()
    try:
        issues = loader.validate(checklist)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Failed to read checklist: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    if issues:
        console.print("[red]Checklist validation failed:[/red]")
        for issue in issues:
            location = issue.path or "checklist"
            console.print(f"- {location}: {issue.message}")
        raise typer.Exit(code=1)
    console.print("[green]Checklist is valid.[/green]")
