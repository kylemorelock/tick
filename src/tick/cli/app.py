"""CLI app with deferred heavy imports."""

from pathlib import Path

import typer

app = typer.Typer(
    name="tick",
    help="tick - Tick off your QA checklists",
    no_args_is_help=True,
    add_completion=False,
)

cache_app = typer.Typer(help="Manage checklist cache")
telemetry_app = typer.Typer(help="Manage telemetry")


@app.command()
def run(
    checklist: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("./reports"), "--output-dir", "-o"),
    no_interactive: bool = typer.Option(False, "--no-interactive"),
    answers: Path | None = typer.Option(None, "--answers", exists=True, readable=True),
    resume: bool = typer.Option(False, "--resume"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview items without starting"),
    cache_dir: Path | None = typer.Option(None, "--cache-dir", help="Override cache directory"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable checklist cache"),
) -> None:
    from tick.cli.commands.run import run_command
    from tick.core.telemetry import telemetry_context
    from tick.logging import configure_logging

    configure_logging(verbose=verbose)
    with telemetry_context("run"):
        run_command(
            checklist=checklist,
            output_dir=output_dir,
            no_interactive=no_interactive,
            answers=answers,
            resume=resume,
            dry_run=dry_run,
            cache_dir=cache_dir,
            no_cache=no_cache,
        )


@app.command()
def validate(
    checklist: Path = typer.Argument(..., exists=True, readable=True),
    cache_dir: Path | None = typer.Option(None, "--cache-dir", help="Override cache directory"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable checklist cache"),
) -> None:
    from tick.cli.commands.validate import validate_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("validate"):
        validate_command(checklist=checklist, cache_dir=cache_dir, no_cache=no_cache)


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
    from tick.core.telemetry import telemetry_context

    with telemetry_context("report"):
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
    from tick.core.telemetry import telemetry_context

    with telemetry_context("init"):
        init_command(template=template, output=output, overwrite=overwrite)


@app.command("templates")
def list_templates() -> None:
    from tick.cli.commands.templates import templates_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("templates"):
        templates_command()


@app.command()
def info() -> None:
    from tick.cli.commands.info import info_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("info"):
        info_command()


@cache_app.command("info")
def cache_info(
    cache_dir: Path | None = typer.Option(None, "--cache-dir", help="Override cache directory"),
) -> None:
    from tick.cli.commands.cache import cache_info as cache_info_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("cache.info"):
        cache_info_command(cache_dir=cache_dir)


@cache_app.command("clean")
def cache_clean(
    cache_dir: Path | None = typer.Option(None, "--cache-dir", help="Override cache directory"),
) -> None:
    from tick.cli.commands.cache import cache_clean as cache_clean_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("cache.clean"):
        cache_clean_command(cache_dir=cache_dir)


@cache_app.command("prune")
def cache_prune(
    cache_dir: Path | None = typer.Option(None, "--cache-dir", help="Override cache directory"),
    days: int = typer.Option(30, "--days", min=1, help="Remove entries older than N days"),
) -> None:
    from tick.cli.commands.cache import cache_prune as cache_prune_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("cache.prune"):
        cache_prune_command(cache_dir=cache_dir, days=days)


@telemetry_app.command("enable")
def telemetry_enable() -> None:
    from tick.cli.commands.telemetry import telemetry_enable as telemetry_enable_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("telemetry.enable"):
        telemetry_enable_command()


@telemetry_app.command("disable")
def telemetry_disable() -> None:
    from tick.cli.commands.telemetry import telemetry_disable as telemetry_disable_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("telemetry.disable"):
        telemetry_disable_command()


@telemetry_app.command("status")
def telemetry_status() -> None:
    from tick.cli.commands.telemetry import telemetry_status as telemetry_status_command
    from tick.core.telemetry import telemetry_context

    with telemetry_context("telemetry.status"):
        telemetry_status_command()


app.add_typer(cache_app, name="cache")
app.add_typer(telemetry_app, name="telemetry")
