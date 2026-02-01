# Contributing

Thanks for helping improve tick! We welcome bug reports, feature ideas, and pull requests.

## Code of conduct

By participating, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to contribute

- **Bug reports and feature requests:** Open an [issue](https://github.com/kylemorelock/tick/issues). Use the Bug report or Feature request template when possible.
- **Security issues:** Please report privately; see [SECURITY.md](SECURITY.md).
- **Pull requests:** See below. For large changes, open an issue first to discuss.

## Development setup

```bash
git clone https://github.com/kylemorelock/tick.git && cd tick
uv sync
```

Optional: install [pre-commit](https://pre-commit.com) so lint and format run before each commit:

```bash
uv run pre-commit install
```

## Running tests and checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest
```

- Default `pytest` runs unit tests with 90% coverage.
- Integration: `uv run pytest -m integration --no-cov`
- E2E: `uv run pytest -m e2e --no-cov`

See [AGENTS.md](AGENTS.md) for test tiers and conventions.

## Pull requests

- Keep changes focused and include tests when possible.
- Update documentation for user-facing changes (README, `docs/`, CLI help).
- Add a changelog entry in [CHANGELOG.md](CHANGELOG.md) for user-visible changes.
- Ensure CI passes (lint, typecheck, unit tests; integration and e2e run in CI as well).

## Releasing

When cutting a release, update the version in `pyproject.toml` only; the package reads it from there when installed. Tag with `v*` (e.g. `v0.1.0`) to trigger the release workflow.
