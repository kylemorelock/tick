from __future__ import annotations

from rich.console import Console
from rich.progress import Progress


def run_progress(total: int, console: Console) -> Progress:
    progress = Progress(console=console)
    progress.add_task("Checklist progress", total=total)
    return progress
