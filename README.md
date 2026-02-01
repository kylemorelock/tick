# tick ✅

[![CI](https://github.com/kylemorelock/tick/actions/workflows/ci.yaml/badge.svg)](https://github.com/kylemorelock/tick/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

tick is a CLI tool for QA engineers to execute configurable testing checklists. It reads
YAML checklists, guides users through each item, records responses, and generates reports
that are ready to share.

## Install

**From source (recommended for development):**

```bash
git clone https://github.com/kylemorelock/tick.git && cd tick
uv sync
```

**From PyPI (after first release):**

```bash
pip install tick
# or: uv add tick
```

## 🚀 Quick start

```bash
uv sync
uv run tick --help
```

### One-minute workflow

```bash
# Initialize a new checklist from a template
uv run tick init --template web > my-checklist.yaml

# Validate the checklist
uv run tick validate my-checklist.yaml

# Run it interactively (creates a session JSON)
uv run tick run my-checklist.yaml --output-dir ./reports

# Generate a report from the session
uv run tick report ./reports/session-<id>.json --format html
```

## ✨ Why tick

- Guides QA runs with a friendly interactive TUI (pass/fail/skip/na).
- Supports variables, conditions, and matrix expansions for dynamic checklists.
- Captures notes and evidence for every item.
- Stores resumable sessions as JSON with integrity checks.
- Generates HTML, Markdown, or JSON reports.
- Ships with built-in checklist templates.

## 📚 Core concepts

- **Checklist**: A YAML file describing sections, items, and optional variables.
- **Session**: A JSON record of a run (responses, variables, timestamps).
- **Report**: A rendered view of a session (HTML/Markdown/JSON).

## 💻 CLI reference

All commands support `--help`. Options below reflect the current CLI.

### `tick run`

Execute a checklist interactively or in non-interactive mode.

```bash
tick run [OPTIONS] CHECKLIST
```

Options:
- `CHECKLIST` (required): Path to a `.yaml`/`.yml` checklist file.
- `--output-dir`, `-o`: Directory to store session JSON (default `./reports`).
- `--no-interactive`: Run without prompts (uses answers file and defaults).
- `--answers`: Path to answers YAML (used with `--no-interactive`).
- `--resume`: Resume the most recent in-progress session for this checklist.
- `--verbose`, `-v`: Enable verbose logging to stderr for debugging.
- `--dry-run`: Preview which items would be included without starting a session.

Notes:
- `--resume` cannot be combined with `--no-interactive` or `--answers`.
- `--dry-run` cannot be combined with `--resume`.
- If `--no-interactive` is used and a required variable is missing, the run fails.
- Unanswered items in non-interactive mode default to `skip`.
- In interactive mode, progress is auto-saved after each response, so you can safely
  interrupt with Ctrl+C and resume later with `--resume`.
- In interactive mode, type `back` or `b` to return to the previous item and change
  your response.

### `tick validate`

Validate a checklist file against the schema.

```bash
tick validate CHECKLIST
```

Options:
- `CHECKLIST` (required): Path to checklist YAML.

### `tick report`

Generate a report from a saved session.

```bash
tick report [OPTIONS] SESSION
```

Options:
- `SESSION` (required): Path to a `session-*.json` file.
- `--format`, `-f`: `html` (default), `json`, `md`, or `markdown`.
- `--checklist`: Path to checklist YAML (required if session lacks a saved path).
- `--output`, `-o`: Output file path (defaults to session path with new extension).
- `--overwrite`: Overwrite existing output file.
- `--template`: Path to a custom Jinja2 template (HTML format only).

### `tick init`

Initialize a new checklist from a built-in template.

```bash
tick init [OPTIONS]
```

Options:
- `--template`, `-t`: `web` (default), `api`, or `accessibility`.
- `--output`, `-o`: Output file path (prints to stdout if omitted).
- `--overwrite`: Overwrite existing output file.

### `tick templates`

List available checklist templates.

```bash
tick templates
```

## 📋 Checklist schema

Checklists are YAML files with a top-level `checklist` object.
See `docs/checklist-schema.md` for the full schema reference.

```yaml
checklist:
  name: "Web Application QA Checklist"
  version: "1.0.0"
  domain: "web"
  metadata:
    author: "QA Team"
    tags: ["web", "smoke"]
    estimated_time: "1 hour"
  variables:
    environment:
      prompt: "Environment"
      options: ["dev", "staging", "prod"]
      required: true
  sections:
    - name: "Authentication"
      items:
        - id: "auth-001"
          check: "Verify password complexity requirements"
          severity: "critical"
          guidance: "Try weak passwords and confirm they are rejected."
          evidence_required: true
```

Supported fields:
- `metadata`: `author`, `tags`, `estimated_time`.
- `variables`: prompt users at runtime (`prompt`, `required`, `options`, `default`).
- `sections`: list of section objects (`name`, optional `condition`, `items`).
- `items`: list of checks (`id`, `check`, optional `severity`, `guidance`,
  `evidence_required`, `condition`, `matrix`).
- `severity` values: `low`, `medium`, `high`, `critical` (defaults to `medium`).

## 🔀 Conditions and matrices

Use `condition` to include sections/items only when variable expressions are true.
Supported expression features include:
- Equality/inequality: `==`, `!=`
- Membership: `in`, `not in`
- Boolean logic: `and`, `or`, `not`
- Lists/tuples and string/boolean constants

Invalid or unsafe expressions raise an error so you can fix the checklist.

Matrix items expand a single checklist item into multiple rows:

```yaml
items:
  - id: "role-access"
    check: "Verify role access rules"
    matrix:
      - role: "user"
      - role: "admin"
```

Each matrix entry becomes a distinct item in the run, with the matrix values shown
in the prompt and attached to the response.

## 🤖 Non-interactive runs and answers file

Use `--no-interactive` to drive runs from a YAML answers file.

```yaml
variables:
  environment: "staging"
responses:
  auth-001:
    result: pass
    notes: "Policy enforced"
    evidence: "screenshot.png, audit-log.txt"
  auth-002:
    result: fail
```

Responses can also be a list of entries, which is required to disambiguate matrix
items:

```yaml
responses:
  - item_id: "role-access"
    matrix:
      role: "admin"
    result: pass
    notes: "Admin can access settings"
```

Rules:
- `variables` must be a mapping. Required variables must be present or have defaults.
- `responses` can be a mapping (`id -> response`) or a list with `item_id`.
- `result` accepts `pass`, `fail`, `skip`, `na` (case-insensitive; `p/f/s/n` ok).
- `evidence` can be a comma-separated string or a list.
- Unmatched responses are ignored with a warning; missing responses default to `skip`.

## 📊 Reports

`tick report` supports:
- `html`: rich, shareable report using the built-in template.
- `md`/`markdown`: a compact Markdown table.
- `json`: raw checklist + session data for automation.

Reports are written next to the session by default, using the correct extension.
If a session references a checklist outside the session directory, pass `--checklist`
explicitly.
The output directory may also include a `session-index.json` to speed listing/resume.

## 📦 Built-in templates

Templates are bundled for quick starts:
- `web`
- `api`
- `accessibility`

To list them:

```bash
tick templates
```

## 🗂️ Project layout

```
src/tick/
  cli/            # Typer CLI and Rich UI
  core/           # Models, engine, protocols, validation
  adapters/       # YAML loader, reporters, storage
  templates/      # Built-in checklists and report templates
tests/            # Unit, integration, e2e tests
```

## 🧪 Development

### Running tests

tick uses pytest with three test tiers:

| Tier | Marker | Purpose | Coverage |
|------|--------|---------|----------|
| **Unit** | `@pytest.mark.unit` | Fast, isolated tests | 90% required |
| **Integration** | `@pytest.mark.integration` | Component boundaries | No gate |
| **E2E** | `@pytest.mark.e2e` | Full CLI workflows | No gate |

```bash
# Run unit tests with coverage (default)
uv run pytest

# Run integration tests
uv run pytest -m integration --no-cov

# Run e2e tests
uv run pytest -m e2e --no-cov

# Run all tests
uv run pytest -m "unit or integration or e2e" --no-cov
```

Tests are auto-marked based on directory location (`tests/unit/`, `tests/integration/`, `tests/e2e/`).

### Linting and type checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```

## 🔧 Extending tick

- Add reporters in `src/tick/adapters/reporters` and register them in
  `src/tick/cli/commands/report.py`.
- Add new checklist loaders by implementing `ChecklistLoader` from
  `src/tick/core/protocols.py`.

## License

tick is released under the [MIT License](LICENSE).
 