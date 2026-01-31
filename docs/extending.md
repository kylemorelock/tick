# Extending tick

## Add new reporters

Implement a new reporter in `src/tick/adapters/reporters` and register it in
`src/tick/cli/commands/report.py`.

Example:

```python
from tick.adapters.reporters.base import ReporterBase
from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


class TextReporter(ReporterBase):
    content_type = "text/plain"
    file_extension = "txt"

    def generate(self, session: Session, checklist: Checklist) -> bytes:
        return f"{checklist.name} ({session.id})".encode("utf-8")
```

Then add it to `_REPORTERS` in `src/tick/cli/commands/report.py`.

## Add new checklist loaders

Implement the `ChecklistLoader` protocol from `tick.core.protocols` and wire it
into the CLI commands.

Example:

```python
from pathlib import Path

from tick.core.models.checklist import Checklist
from tick.core.protocols import ChecklistLoader
from tick.core.validator import ValidationIssue


class JsonChecklistLoader(ChecklistLoader):
    def load(self, path: Path) -> Checklist:
        raise NotImplementedError

    def validate(self, path: Path) -> list[ValidationIssue]:
        return []
```
