# Getting started

## Install (end users)

```bash
pipx install tick
# or: uv tool install tick
```

## Install dependencies (from source)

```bash
uv sync
```

## Start from a template

```bash
uv run tick init --template web --output my-checklist.yaml
```

List available templates:

```bash
uv run tick templates
```

## Validate a checklist

```bash
uv run tick validate my-checklist.yaml
```

## Run interactively

```bash
uv run tick run my-checklist.yaml --output-dir ./reports
```

## Run non-interactively

Create an answers file:

```yaml
variables:
  environment: "staging"
responses:
  auth-001:
    result: pass
    evidence: "screenshot.png"
```

Then run:

```bash
uv run tick run my-checklist.yaml --no-interactive --answers answers.yaml
```

## Resume a session

```bash
uv run tick run my-checklist.yaml --resume
```

## Generate a report

```bash
uv run tick report ./reports/session-<id>.json --format html --output report.html
```

Supported formats: `html`, `json`, `md`, `markdown`.
If the stored checklist path is outside the session directory, pass `--checklist`.

## Single-binary (optional)

tick can be packaged as a standalone binary using tools like PyInstaller or PyOxidizer.
This is optional, but useful for locked-down environments.
