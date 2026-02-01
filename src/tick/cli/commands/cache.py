from __future__ import annotations

from pathlib import Path

from rich.console import Console

from tick.core.cache import ChecklistCache


def cache_info(cache_dir: Path | None = None) -> None:
    console = Console()
    cache = ChecklistCache(cache_dir)
    stats = cache.stats()
    console.print(f"[bold]Cache directory:[/bold] {cache.cache_dir}")
    console.print(f"Checklist entries: {stats.checklist_entries}")
    console.print(f"Expansion entries: {stats.expansion_entries}")
    console.print(f"Total size: {stats.total_bytes} bytes")


def cache_clean(cache_dir: Path | None = None) -> None:
    console = Console()
    cache = ChecklistCache(cache_dir)
    cache.clean()
    console.print(f"[green]Cache cleared:[/green] {cache.cache_dir}")


def cache_prune(cache_dir: Path | None = None, days: int = 30) -> None:
    console = Console()
    cache = ChecklistCache(cache_dir)
    cache.prune(max_age_days=days)
    console.print(f"[green]Cache pruned (>{days} days):[/green] {cache.cache_dir}")
