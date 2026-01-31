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
uv run pytest
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

- Use `tmp_path` for file IO.
- Prefer fixtures for checklists/sessions.
- Assert exit codes for CLI failure paths.
