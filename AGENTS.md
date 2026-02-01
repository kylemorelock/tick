---
title: Agents Guide for tick
---

# Agents Guide for tick

This repo is a CLI tool for running QA checklists defined in YAML. The main goals are
clarity for testers, safe execution, and dependable reporting.

## Quick commands

```bash
uv sync
uv run tick --help
uv run tick run my-checklist.yaml --output-dir ./reports
uv run tick report ./reports/session-<id>.json --format html

# Run tests (unit tests with 90% coverage gate)
uv run pytest

# Run integration or e2e tests separately
uv run pytest -m integration --no-cov
uv run pytest -m e2e --no-cov
```

## Architecture at a glance

- `src/tick/cli`: Typer CLI and Rich UI prompts.
- `src/tick/core`: engine, models, protocols, validation.
- `src/tick/adapters`: YAML loader, reporters, session storage.
- `src/tick/templates`: built-in checklist templates + report template.
- `tests`: unit/integration/e2e tests.

## Behavioral invariants

- `tick run` stores sessions as `reports/session-<id>.json`.
- `--resume` is mutually exclusive with `--no-interactive` and `--answers`.
- Non-interactive runs default to `skip` for missing responses.
- `tick report` verifies checklist digest and rejects mismatches.
- Session JSON is encoded/decoded with `msgspec`.

## Checklist schema highlights

- Top-level `checklist` object with `name`, `version`, `domain`, `sections`.
- `variables` prompt at runtime and can be required, have options, or defaults.
- `condition` gates sections/items using safe boolean expressions only.
- `matrix` expands one item into multiple items at runtime.

## Editing guidelines

- Keep CLI imports light in `src/tick/cli/app.py` and `src/tick/__main__.py`.
- Use `Path` and explicit `utf-8` encoding for file operations.
- Fail fast in CLI commands with `typer.Exit(code=1)` and a user-facing message.
- Update docs whenever CLI flags, schema, or output formats change.

## Tests

Three test tiers, auto-marked by directory location:

- `tests/unit/` → `@pytest.mark.unit` — Fast, isolated tests. **90% coverage required.**
- `tests/integration/` → `@pytest.mark.integration` — Component boundaries (loader+models, engine+storage, reporters).
- `tests/e2e/` → `@pytest.mark.e2e` — Full CLI workflows with CliRunner.

### Running tests

```bash
# Default: unit tests with coverage gate
uv run pytest

# Integration tests (no coverage gate)
uv run pytest -m integration --no-cov

# E2E tests (no coverage gate)
uv run pytest -m e2e --no-cov

# All tests without coverage
uv run pytest -m "unit or integration or e2e" --no-cov
```

### Test patterns

- Use `tmp_path` for file IO.
- Prefer fixtures for checklists/sessions (see `tests/conftest.py`).
- Assert exit codes for CLI failure paths.
- For interactive CLI tests, patch `run_module.ask_variables` and `run_module.ask_item_response`.
- Integration tests use real implementations (no mocking of internal components).
- E2E tests use `CliRunner` from typer.testing.
