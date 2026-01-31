from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.prompt import Confirm, Prompt

from tick.core.models.checklist import ChecklistVariable
from tick.core.models.enums import ItemResult
from tick.core.state import ResolvedItem

RESULT_CHOICES = {
    "pass": ItemResult.PASS,
    "p": ItemResult.PASS,
    "fail": ItemResult.FAIL,
    "f": ItemResult.FAIL,
    "skip": ItemResult.SKIP,
    "s": ItemResult.SKIP,
    "na": ItemResult.NOT_APPLICABLE,
    "n": ItemResult.NOT_APPLICABLE,
}


def _prompt_result(console: Console) -> ItemResult:
    while True:
        response = Prompt.ask(
            "Result (pass/p, fail/f, skip/s, na/n)",
            default="pass",
            console=console,
        )
        normalized = response.strip().lower()
        result = RESULT_CHOICES.get(normalized)
        if result:
            return result
        console.print("[red]Please enter one of: pass/p, fail/f, skip/s, na/n.[/red]")


def ask_variables(variables: dict[str, ChecklistVariable], console: Console) -> dict[str, str]:
    results: dict[str, str] = {}
    for key, spec in variables.items():
        if spec.required:
            console.print("[dim]Required input.[/dim]")
        if spec.options:
            console.print(f"[dim]Options: {', '.join(spec.options)}[/dim]")
        if spec.default is not None:
            console.print(f"[dim]Default: {spec.default}[/dim]")
        prompt_text = spec.prompt
        if spec.options:
            value = Prompt.ask(
                prompt_text,
                choices=spec.options,
                default=spec.default,
                console=console,
            )
            while spec.required and not value:
                value = Prompt.ask(
                    prompt_text,
                    choices=spec.options,
                    default=spec.default,
                    console=console,
                )
        else:
            value = Prompt.ask(prompt_text, default=spec.default, console=console)
            while spec.required and not value:
                value = Prompt.ask(prompt_text, default=spec.default, console=console)
        if value is None:
            continue
        results[key] = value
    return results


def ask_item_response(
    item: ResolvedItem, console: Console
) -> tuple[ItemResult, str | None, Iterable[str]]:
    console.print(f"\n[bold]{item.section_name}[/bold]")
    console.print(f"{item.display_check}")
    if item.item.guidance:
        console.print(f"[dim]{item.item.guidance}[/dim]")
    console.print("[dim]Result options: pass (p), fail (f), skip (s), not applicable (na/n).[/dim]")
    result = _prompt_result(console)
    notes = Prompt.ask("Notes (optional, press enter to skip)", default="", console=console)
    notes_value = notes or None
    evidence_entries: Iterable[str] = ()
    if item.item.evidence_required or Confirm.ask("Add evidence?", default=False, console=console):
        evidence = Prompt.ask(
            "Evidence (comma-separated, optional)",
            default="",
            console=console,
        )
        evidence_entries = [entry.strip() for entry in evidence.split(",") if entry.strip()]
    return result, notes_value, evidence_entries
