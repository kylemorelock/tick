# Extending tick

## Custom HTML templates

You can provide a custom Jinja2 template for HTML reports using the `--template`
flag:

```bash
tick report session.json --format html --template ./my-template.j2
```

The template receives these variables:

- `checklist`: The checklist object (name, version, domain, metadata, sections)
- `session`: The session object (id, started_at, completed_at, status, variables, responses)
- `rows`: List of response rows, each with: id, check, severity, result, notes, evidence, matrix
- `stats`: Summary statistics dict with keys: pass, fail, skip, na, total

Example minimal template:

```html
<!DOCTYPE html>
<html>
<head><title>{{ checklist.name }}</title></head>
<body>
  <h1>{{ checklist.name }}</h1>
  <p>Total: {{ stats.total }} | Pass: {{ stats.pass }} | Fail: {{ stats.fail }}</p>
  <ul>
  {% for row in rows %}
    <li>{{ row.id }}: {{ row.result }}</li>
  {% endfor %}
  </ul>
</body>
</html>
```

See `src/tick/templates/reports/report.html.j2` for the full built-in template.

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
