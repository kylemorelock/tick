from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console

from tick.core.telemetry import get_telemetry_state, set_telemetry_enabled, telemetry_enabled


def telemetry_enable() -> None:
    console = Console()
    set_telemetry_enabled(True)
    console.print("[green]Telemetry enabled.[/green]")


def telemetry_disable() -> None:
    console = Console()
    set_telemetry_enabled(False)
    console.print("[yellow]Telemetry disabled.[/yellow]")


def telemetry_status() -> None:
    console = Console()
    enabled = telemetry_enabled()
    state = get_telemetry_state()
    console.print(f"[bold]Telemetry:[/bold] {'enabled' if enabled else 'disabled'}")
    console.print(f"[bold]Commands recorded:[/bold] {sum(state.commands.values())}")
    console.print(f"[bold]Errors recorded:[/bold] {sum(state.errors.values())}")
    if state.last_event_at:
        timestamp = datetime.fromtimestamp(state.last_event_at, tz=UTC).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        console.print(f"[bold]Last event:[/bold] {timestamp}")
