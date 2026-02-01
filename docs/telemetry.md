# Telemetry (opt-in)

tick includes optional, privacy-first telemetry. It is **disabled by default**.

## What is collected

- Command name (e.g., `run`, `validate`, `report`)
- Duration bucket (coarse timing, not exact timestamps)
- Error type (if a command fails)

No file paths, checklist contents, answers, or user identifiers are collected.

## Where it is stored

Telemetry is stored locally in your user config directory. There is no network
transmission.

## Commands

```bash
tick telemetry enable
tick telemetry disable
tick telemetry status
```

To remove local data entirely, delete the telemetry files in your config directory
or disable telemetry and remove the folder.
