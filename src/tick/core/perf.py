from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.adapters.reporters.html import HtmlReporter
from tick.core.engine import _expand_items
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session
from tick.core.state import ResolvedItem


@dataclass(frozen=True)
class PerfResult:
    validate_seconds: float
    expand_seconds: float
    report_seconds: float
    items: int


def _build_session(
    checklist_id: str,
    items: Sequence[ResolvedItem],
    variables: Mapping[str, object],
) -> Session:
    now = datetime.now(UTC)
    session = Session(
        id="perf-session",
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=now,
        completed_at=now,
        status=SessionStatus.COMPLETED,
        variables={k: str(v) for k, v in variables.items()},
        responses=[],
    )
    for resolved in items:
        response = Response(
            item_id=resolved.item.id,
            result=ItemResult.PASS,
            answered_at=now,
            notes=None,
            evidence=(),
            matrix_context=resolved.matrix_context,
        )
        session.responses.append(response)
    return session


def run_harness(checklist_path: Path, variables: Mapping[str, object] | None = None) -> PerfResult:
    variables = variables or {}
    loader = YamlChecklistLoader()

    validate_start = perf_counter()
    issues = loader.validate(checklist_path)
    validate_end = perf_counter()
    if issues:
        formatted = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        raise ValueError(f"Checklist validation failed: {formatted}")

    expand_start = perf_counter()
    checklist = loader.load(checklist_path)
    items = _expand_items(checklist, variables)
    expand_end = perf_counter()

    report_start = perf_counter()
    session = _build_session(checklist.checklist_id, items, variables)
    HtmlReporter().generate(session, checklist)
    report_end = perf_counter()

    return PerfResult(
        validate_seconds=validate_end - validate_start,
        expand_seconds=expand_end - expand_start,
        report_seconds=report_end - report_start,
        items=len(items),
    )


def _format_result(result: PerfResult) -> str:
    return (
        f"items: {result.items}\n"
        f"validate_seconds: {result.validate_seconds:.4f}\n"
        f"expand_seconds: {result.expand_seconds:.4f}\n"
        f"report_seconds: {result.report_seconds:.4f}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="tick performance harness")
    parser.add_argument("checklist", type=Path, help="Path to checklist YAML")
    args = parser.parse_args(argv)

    result = run_harness(args.checklist)
    print(_format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
