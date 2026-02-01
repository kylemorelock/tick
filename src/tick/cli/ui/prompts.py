from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.prompt import Confirm, Prompt

from tick.core.models.checklist import ChecklistVariable
from tick.core.models.enums import ItemResult
from tick.core.state import ResolvedItem

RESULT_CHOICES: dict[str, ItemResult | None] = {
    "pass": ItemResult.PASS,
    "p": ItemResult.PASS,
    "fail": ItemResult.FAIL,
    "f": ItemResult.FAIL,
    "skip": ItemResult.SKIP,
    "s": ItemResult.SKIP,
    "na": ItemResult.NOT_APPLICABLE,
    "n": ItemResult.NOT_APPLICABLE,
    "back": None,  # Special sentinel for going back
    "b": None,
}


def _prompt_result(console: Console, can_go_back: bool = False) -> ItemResult | None:
    """Prompt for a result. Returns None if user wants to go back."""
    back_hint = ", back/b" if can_go_back else ""
    while True:
        response = Prompt.ask(
            f"Result (pass/p, fail/f, skip/s, na/n{back_hint})",
            default="pass",
            console=console,
        )
        normalized = response.strip().lower()
        if normalized in RESULT_CHOICES:
            result = RESULT_CHOICES[normalized]
            if result is None and not can_go_back:
                console.print("[red]Cannot go back - this is the first item.[/red]")
                continue
            return result
        valid_options = "pass/p, fail/f, skip/s, na/n" + (", back/b" if can_go_back else "")
        console.print(f"[red]Please enter one of: {valid_options}.[/red]")


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
    item: ResolvedItem, console: Console, can_go_back: bool = False
) -> tuple[ItemResult | None, str | None, Iterable[str]]:
    """Prompt for an item response.

    Args:
        item: The checklist item to prompt for.
        console: Rich console for output.
        can_go_back: If True, allow user to type 'back' to go to previous item.

    Returns:
        Tuple of (result, notes, evidence). Result is None if user wants to go back.
    """
    console.print(f"\n[bold]{item.section_name}[/bold]")
    console.print(f"{item.display_check}")
    if item.item.guidance:
        console.print(f"[dim]{item.item.guidance}[/dim]")
    back_hint = ", back (b)" if can_go_back else ""
    opts = f"pass (p), fail (f), skip (s), not applicable (na/n){back_hint}"
    console.print(f"[dim]Result options: {opts}.[/dim]")
    result = _prompt_result(console, can_go_back=can_go_back)

    # If user wants to go back, return early with None result
    if result is None:
        return None, None, ()

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
