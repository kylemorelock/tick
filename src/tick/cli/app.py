"""CLI app with deferred heavy imports."""

from pathlib import Path

import typer

app = typer.Typer(
    name="tick",
    help="tick - Tick off your QA checklists",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def run(
    checklist: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("./reports"), "--output-dir", "-o"),
    no_interactive: bool = typer.Option(False, "--no-interactive"),
    answers: Path | None = typer.Option(None, "--answers", exists=True, readable=True),
    resume: bool = typer.Option(False, "--resume"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview items without starting"),
) -> None:
    from tick.cli.commands.run import run_command
    from tick.logging import configure_logging

    configure_logging(verbose=verbose)
    run_command(
        checklist=checklist,
        output_dir=output_dir,
        no_interactive=no_interactive,
        answers=answers,
        resume=resume,
        dry_run=dry_run,
    )


@app.command()
def validate(checklist: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    from tick.cli.commands.validate import validate_command

    validate_command(checklist=checklist)


@app.command()
def report(
    session: Path = typer.Argument(..., exists=True, readable=True),
    format: str = typer.Option("html", "--format", "-f"),
    checklist: Path | None = typer.Option(None, "--checklist"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    template: Path | None = typer.Option(
        None,
        "--template",
        exists=True,
        readable=True,
        help="Custom Jinja2 template for HTML reports",
    ),
) -> None:
    from tick.cli.commands.report import report_command

    report_command(
        session_path=session,
        format=format,
        checklist_path=checklist,
        output_path=output,
        overwrite=overwrite,
        template_path=template,
    )


@app.command()
def init(
    template: str = typer.Option("web", "--template", "-t"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    from tick.cli.commands.init import init_command

    init_command(template=template, output=output, overwrite=overwrite)


@app.command("templates")
def list_templates() -> None:
    from tick.cli.commands.templates import templates_command

    templates_command()
