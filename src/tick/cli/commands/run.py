from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import structlog
import typer
from rich.console import Console
from rich.progress import Progress
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.adapters.storage.session_store import SessionStore
from tick.cli.ui.prompts import ask_item_response, ask_variables
from tick.cli.ui.tables import render_summary
from tick.core.engine import ExecutionEngine
from tick.core.models.checklist import ChecklistVariable
from tick.core.models.enums import ItemResult
from tick.core.utils import ensure_session_digest, matrix_key, normalize_evidence

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def _load_answers(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle)
    except (OSError, YAMLError) as exc:
        raise ValueError("Failed to read answers file.") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Answers file must be a mapping at the top level.")
    return data


def _normalize_responses(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    responses = data.get("responses", {})
    normalized: list[dict[str, Any]] = []
    if isinstance(responses, dict):
        for item_id, entry in responses.items():
            if entry is None:
                entry = {}
            if isinstance(entry, dict):
                entry = {**entry, "item_id": item_id}
                normalized.append(entry)
    elif isinstance(responses, list):
        normalized.extend(e for e in responses if isinstance(e, dict) and "item_id" in e)
    response_map: dict[str, list[dict[str, Any]]] = {}
    for entry in normalized:
        response_map.setdefault(str(entry["item_id"]), []).append(entry)
    return response_map


def _resolve_variables(
    variables: dict[str, Any], specs: dict[str, ChecklistVariable]
) -> tuple[dict[str, object], list[str]]:
    normalized: dict[str, object] = {}
    errors: list[str] = []
    for key, spec in specs.items():
        value = variables.get(key)
        if value in (None, "") and spec.default is not None:
            value = spec.default
        if value in (None, ""):
            if spec.required:
                errors.append(f"Missing required variable: {key}")
            continue
        value_str = str(value)
        if spec.options and value_str not in spec.options:
            errors.append(f"Invalid value for {key}: {value_str}")
            continue
        normalized[key] = value_str if spec.options else value
    return normalized, errors


def _parse_result(value: str | None) -> ItemResult:
    if not value:
        return ItemResult.SKIP
    normalized = value.strip().lower()
    if normalized in {"pass", "p"}:
        return ItemResult.PASS
    if normalized in {"fail", "f"}:
        return ItemResult.FAIL
    if normalized in {"skip", "s"}:
        return ItemResult.SKIP
    if normalized in {"na", "n", "not_applicable", "not-applicable"}:
        return ItemResult.NOT_APPLICABLE
    return ItemResult.SKIP


def _ensure_output_dir(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:
        raise ValueError("Output directory is not a directory.") from exc
    if not output_dir.is_dir():
        raise ValueError("Output directory is not a directory.")  # pragma: no cover - defensive
    if not os.access(output_dir, os.W_OK):
        raise ValueError("Output directory is not writable.")


def run_command(
    checklist: Path,
    output_dir: Path,
    no_interactive: bool,
    answers: Path | None,
    resume: bool,
    dry_run: bool = False,
    cache_dir: Path | None = None,
    no_cache: bool = False,
) -> None:
    console = Console()
    log.debug("run_command_start", checklist=str(checklist), output_dir=str(output_dir))
    from tick.core.cache import ChecklistCache

    cache = None if no_cache else ChecklistCache(cache_dir)
    if resume and (answers or no_interactive):
        console.print("[red]Resume cannot be combined with --answers or --no-interactive.[/red]")
        raise typer.Exit(code=1)
    if dry_run and resume:
        console.print("[red]Dry-run cannot be combined with --resume.[/red]")
        raise typer.Exit(code=1)
    loader = YamlChecklistLoader(cache=cache)
    try:
        checklist_model = loader.load(checklist)
        log.debug("checklist_loaded", checklist_id=checklist_model.checklist_id)
    except (OSError, ValueError) as exc:
        log.error("checklist_load_failed", error=str(exc))
        console.print(f"[red]Failed to load checklist: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    # Handle dry-run mode early
    if dry_run:
        from tick.core.engine import _expand_items_cached

        try:
            answers_data = _load_answers(answers)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        variables_data = answers_data.get("variables", {})
        if not isinstance(variables_data, dict):
            variables_data = {}
        resolved_vars, errors = _resolve_variables(variables_data, checklist_model.variables)
        if errors:
            for error in errors:
                console.print(f"[yellow]Warning: {error}[/yellow]")
            # Continue with available variables for preview

        items = _expand_items_cached(checklist_model, resolved_vars, cache)
        console.print(f"[bold]Checklist: {checklist_model.name}[/bold]")
        console.print(f"Version: {checklist_model.version}")
        console.print(f"Domain: {checklist_model.domain}")
        console.print()
        console.print(f"[bold]Would run {len(items)} items:[/bold]")
        for item in items:
            console.print(f"  - [{item.item.severity.value}] {item.display_check}")
        raise typer.Exit(0)

    try:
        _ensure_output_dir(output_dir)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    store = SessionStore(output_dir)
    engine = ExecutionEngine(loader=loader, storage=store, cache=cache)

    try:
        answers_data = _load_answers(answers)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    if resume:
        session = store.find_latest_in_progress(checklist_model.checklist_id)
        if not session:
            console.print("[red]No in-progress session found to resume.[/red]")
            raise typer.Exit(code=1)
        if ensure_session_digest(session, checklist_model):
            store.save(session)
        try:
            engine.resume(checklist_model, session)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
        completed = len(engine.state.session.responses)
        total = len(engine.state.items)
        console.print(
            f"[yellow]Resuming session {session.id} ({completed}/{total} complete)[/yellow]"
        )
    else:
        if no_interactive:
            variables_data = answers_data.get("variables", {})
            if not isinstance(variables_data, dict):
                console.print("[red]Answers file variables must be a mapping.[/red]")
                raise typer.Exit(code=1)
            resolved_vars, errors = _resolve_variables(variables_data, checklist_model.variables)
            if errors:
                for error in errors:
                    console.print(f"[red]{error}[/red]")
                raise typer.Exit(code=1)
            variables: Mapping[str, object] = resolved_vars
        else:
            variables = ask_variables(checklist_model.variables, console)
        try:
            checklist_resolved = checklist.resolve()
            try:
                checklist_path_value = str(checklist_resolved.relative_to(output_dir.resolve()))
            except ValueError:
                checklist_path_value = str(checklist_resolved)
            engine.start(checklist_model, variables, checklist_path_value)
            engine.save()  # Save immediately so session exists for resume
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

    total = len(engine.state.items)
    response_map = _normalize_responses(answers_data)

    if no_interactive:
        with Progress(console=console) as progress:
            task = progress.add_task(f"Checklist progress (0/{total})", total=total)
            for item_resolved in engine.state.items[engine.state.current_index :]:
                entry = None
                if response_map.get(item_resolved.item.id):
                    if item_resolved.matrix_context:
                        target = matrix_key(item_resolved.matrix_context)
                        for idx, candidate in enumerate(response_map[item_resolved.item.id]):
                            if matrix_key(candidate.get("matrix")) == target:
                                entry = response_map[item_resolved.item.id].pop(idx)
                                break
                    else:
                        entry = response_map[item_resolved.item.id].pop(0)
                result = _parse_result(entry.get("result") if entry else None)
                notes = entry.get("notes") if entry else None
                evidence = normalize_evidence(entry.get("evidence") if entry else None)
                engine.record_response(
                    item=item_resolved.item,
                    result=result,
                    notes=notes,
                    evidence=evidence or None,
                    matrix_context=item_resolved.matrix_context,
                )
                progress.advance(task)
                progress.update(
                    task,
                    description=f"Checklist progress ({engine.state.current_index}/{total})",
                )
        engine.complete()
        unused = sum(len(entries) for entries in response_map.values())
        if unused:
            msg = (
                f"[yellow]Warning: {unused} answer entries did not match "
                "any checklist item.[/yellow]"
            )
            console.print(msg)
    else:
        try:
            with Progress(console=console) as progress:
                task = progress.add_task(f"Checklist progress (0/{total})", total=total)
                while engine.current_item is not None:
                    current = engine.current_item
                    if current is None:
                        break
                    progress.stop()
                    can_go_back = engine.state.current_index > 0
                    item_result, notes, evidence_iter = ask_item_response(
                        current, console, can_go_back=can_go_back
                    )

                    # Handle back navigation
                    if item_result is None:
                        engine.go_back()
                        engine.save()  # Save after going back
                        idx = engine.state.current_index
                        progress.update(
                            task,
                            completed=idx,
                            description=f"Checklist progress ({idx}/{total})",
                        )
                        progress.start()  # Restart progress before continuing loop
                        continue

                    evidence_list: list[str] | None = list(evidence_iter) if evidence_iter else None
                    progress.start()
                    engine.record_response(
                        item=current.item,
                        result=item_result,
                        notes=notes,
                        evidence=evidence_list,
                        matrix_context=current.matrix_context,
                    )
                    engine.save()  # Auto-save after each response
                    progress.advance(task)
                    progress.update(
                        task,
                        description=f"Checklist progress ({engine.state.current_index}/{total})",
                    )
            engine.complete()
        except KeyboardInterrupt:
            # Session already auto-saved after last response
            completed = len(engine.state.session.responses)
            console.print(
                f"\n[yellow]Interrupted. Session saved with {completed}/{total} responses.[/yellow]"
            )
            console.print("[yellow]Resume later with --resume[/yellow]")
            raise typer.Exit(0) from None

    session_path = store.save(engine.state.session)
    console.print(f"[green]Session saved to {session_path}[/green]")
    render_summary(engine.state.session, console)
