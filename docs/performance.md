# Performance

tick targets fast startup and repeat runs. Use the built-in harness to measure validate,
dry-run expansion, and HTML report generation.

## Benchmark harness

```bash
uv run python -m tick.core.perf /path/to/checklist.yaml
```

The harness measures:
- `validate_seconds`: schema + model validation
- `expand_seconds`: dry-run expansion (variables + matrix)
- `report_seconds`: HTML report generation

## Baseline results

Baseline on **2026-01-31**, **macOS 25.0.0**, **Python 3.12**, **500 items**:

- `validate_seconds`: 0.0656
- `expand_seconds`: 0.0646
- `report_seconds`: 0.0121

## Budgets

These are guardrails to keep UX snappy on typical developer laptops:

- `validate_seconds`: < 1.0s
- `expand_seconds`: < 1.0s
- `report_seconds`: < 0.25s
