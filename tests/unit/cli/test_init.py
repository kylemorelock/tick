from __future__ import annotations

from pathlib import Path

import pytest
import typer

from tick.cli.commands import init as init_module
from tick.cli.commands.init import init_command


def test_init_command_blocks_overwrite(tmp_path: Path) -> None:
    output_path = tmp_path / "template.yaml"
    output_path.write_text("existing")
    with pytest.raises(typer.Exit) as excinfo:
        init_command(template="web", output=output_path, overwrite=False)
    assert excinfo.value.exit_code == 1


def test_init_command_rejects_output_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "outdir"
    output_path.mkdir()
    with pytest.raises(typer.Exit) as excinfo:
        init_command(template="web", output=output_path, overwrite=False)
    assert excinfo.value.exit_code == 1


def test_init_command_template_read_failure(monkeypatch, tmp_path: Path) -> None:
    def fail_files(*_args, **_kwargs):
        raise OSError("boom")

    monkeypatch.setattr(init_module.resources, "files", fail_files)
    with pytest.raises(typer.Exit) as excinfo:
        init_command(template="web", output=tmp_path / "out.yaml", overwrite=False)
    assert excinfo.value.exit_code == 1
