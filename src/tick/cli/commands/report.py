from __future__ import annotations

from pathlib import Path

import typer
from msgspec import DecodeError
from rich.console import Console

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.adapters.reporters.html import HtmlReporter
from tick.adapters.reporters.json import JsonReporter
from tick.adapters.reporters.markdown import MarkdownReporter
from tick.adapters.storage.session_store import SessionStore
from tick.core.models.session import encode_session
from tick.core.utils import atomic_write_bytes, validate_session_digest

_REPORTERS: dict[
    str,
    type[HtmlReporter] | type[JsonReporter] | type[MarkdownReporter],
] = {
    "html": HtmlReporter,
    "json": JsonReporter,
    "md": MarkdownReporter,
    "markdown": MarkdownReporter,
}


def report_command(
    session_path: Path,
    format: str,
    checklist_path: Path | None,
    output_path: Path | None,
    overwrite: bool,
) -> None:
    console = Console()
    if session_path.suffix.lower() != ".json":
        console.print("[red]Session file must be a .json file.[/red]")
        raise typer.Exit(code=1)
    if not session_path.is_file():
        console.print("[red]Session path must be a file.[/red]")
        raise typer.Exit(code=1)
    store = SessionStore(session_path.parent)
    try:
        session = store.load_from_path(session_path)
    except (OSError, ValueError, TypeError, DecodeError) as exc:
        console.print(f"[red]Failed to read session file: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    loader = YamlChecklistLoader()
    if checklist_path is None:
        if not session.checklist_path:
            console.print("[red]Checklist path is required for reporting.[/red]")
            raise typer.Exit(code=1)
        stored_path = Path(session.checklist_path)
        if stored_path.is_absolute():
            try:
                stored_path.resolve().relative_to(session_path.parent.resolve())
            except ValueError as exc:
                console.print(
                    "[red]Stored checklist path is outside the session directory. "
                    "Provide --checklist explicitly.[/red]"
                )
                raise typer.Exit(code=1) from exc
            checklist_path = stored_path
        else:
            if ".." in stored_path.parts:
                console.print("[red]Checklist path contains invalid traversal segments.[/red]")
                raise typer.Exit(code=1)
            checklist_path = (session_path.parent / stored_path).resolve()
    if not checklist_path.is_absolute():
        if ".." in checklist_path.parts:
            console.print("[red]Checklist path contains invalid traversal segments.[/red]")
            raise typer.Exit(code=1)
        checklist_path = checklist_path.resolve()
    if not checklist_path.exists():
        console.print("[red]Checklist file not found.[/red]")
        raise typer.Exit(code=1)
    if checklist_path.suffix.lower() not in {".yaml", ".yml"}:
        console.print("[red]Checklist file must be .yaml or .yml.[/red]")
        raise typer.Exit(code=1)
    try:
        checklist = loader.load(checklist_path)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Failed to load checklist: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    try:
        digest = validate_session_digest(session, checklist)
    except ValueError as exc:
        console.print(f"[red]{exc} Use the original checklist or restart the run.[/red]")
        raise typer.Exit(code=1) from exc
    if session.checklist_digest is None:
        console.print(
            "[yellow]Checklist digest missing in session. "
            "Initializing digest from the provided checklist.[/yellow]"
        )
        session.checklist_digest = digest
        try:
            atomic_write_bytes(session_path, encode_session(session))
        except OSError as exc:
            console.print(f"[red]Failed to update session file: {exc}[/red]")
            raise typer.Exit(code=1) from exc

    reporter_cls = _REPORTERS.get(format.lower())
    if reporter_cls is None:
        valid_formats = ", ".join(sorted(_REPORTERS.keys()))
        console.print(f"[red]Unsupported format: {format}. Use one of: {valid_formats}.[/red]")
        raise typer.Exit(code=1)
    reporter = reporter_cls()
    content = reporter.generate(session, checklist)

    if output_path is None:
        output_path = session_path.with_suffix(f".{reporter.file_extension}")
    if output_path.exists():
        if output_path.is_dir():
            console.print("[red]Output path is a directory.[/red]")
            raise typer.Exit(code=1)
        if not overwrite:
            console.print("[red]Output file already exists. Use --overwrite to replace.[/red]")
            raise typer.Exit(code=1)
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        console.print("[red]Output directory does not exist.[/red]")
        raise typer.Exit(code=1)
    atomic_write_bytes(output_path, content)
    console.print(f"[green]Report written to {output_path}[/green]")
