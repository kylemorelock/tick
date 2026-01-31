from __future__ import annotations

from pathlib import Path

import pytest
import typer

from tick.cli.commands.validate import validate_command


def test_validate_command_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(typer.Exit) as excinfo:
        validate_command(missing)
    assert excinfo.value.exit_code == 1
