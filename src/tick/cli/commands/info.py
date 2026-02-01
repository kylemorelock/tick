from __future__ import annotations

import platform

from rich.console import Console

from tick import __version__
from tick.core.cache import ChecklistCache
from tick.templates.registry import template_keys


def info_command() -> None:
    console = Console()
    cache = ChecklistCache()
    stats = cache.stats()

    console.print(f"[bold]tick version:[/bold] {__version__}")
    console.print(f"[bold]Python:[/bold] {platform.python_version()}")
    console.print(f"[bold]Cache directory:[/bold] {cache.cache_dir}")
    console.print(
        f"[bold]Cache entries:[/bold] "
        f"{stats.checklist_entries} checklists, {stats.expansion_entries} expansions"
    )
    console.print(f"[bold]Templates:[/bold] {', '.join(template_keys())}")
