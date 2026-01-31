from __future__ import annotations

from importlib import resources
from pathlib import Path

import typer
from rich.console import Console

from tick.core.utils import atomic_write_bytes
from tick.templates.registry import template_filename


def init_command(template: str, output: Path | None, overwrite: bool) -> None:
    console = Console()
    template_key = template.lower()
    filename = template_filename(template_key)
    if not filename:
        console.print(f"[red]Unknown template: {template}[/red]")
        raise typer.Exit(code=1)
    try:
        content = (
            resources.files("tick.templates.checklists")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except OSError as exc:
        console.print(f"[red]Failed to load template: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    if output:
        if output.exists() and output.is_dir():
            console.print("[red]Output path is a directory.[/red]")
            raise typer.Exit(code=1)
        if output.exists() and not overwrite:
            console.print("[red]Output file already exists. Use --overwrite to replace.[/red]")
            raise typer.Exit(code=1)
        try:
            atomic_write_bytes(output, content.encode("utf-8"))
        except OSError as exc:
            console.print(f"[red]Failed to write template: {exc}[/red]")
            raise typer.Exit(code=1) from exc
        console.print(f"[green]Wrote template to {output}[/green]")
    else:
        typer.echo(content)
