# Releasing tick

Use this checklist for a clean, repeatable release.

## Checklist

- Update the version in `pyproject.toml`.
- Add release notes to `CHANGELOG.md`.
- Run all tests:
  - `uv run pytest`
  - `uv run pytest -m integration --no-cov`
  - `uv run pytest -m e2e --no-cov`
- Tag the release: `git tag vX.Y.Z`
- Push the tag: `git push origin vX.Y.Z`
- Confirm:
  - GitHub Release was created (from CHANGELOG notes).
  - PyPI publish succeeded (release workflow).
- Announce (optional): README, social, or internal channels.
