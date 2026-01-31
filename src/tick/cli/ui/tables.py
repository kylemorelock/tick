from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.table import Table

from tick.core.models.enums import ItemResult
from tick.core.models.session import Session


def render_summary(session: Session, console: Console) -> None:
    counts = Counter(response.result for response in session.responses)
    table = Table(title="Checklist Summary")
    table.add_column("Result")
    table.add_column("Count", justify="right")
    for result in ItemResult:
        table.add_row(result.value, str(counts.get(result, 0)))
    console.print(table)
