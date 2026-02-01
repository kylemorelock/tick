from __future__ import annotations

import pytest
import typer

from tick.core.telemetry import (
    get_telemetry_state,
    record_event,
    set_telemetry_enabled,
    telemetry_context,
    telemetry_enabled,
)


def test_telemetry_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert telemetry_enabled() is False
    record_event("run", 0.2, None)
    state = get_telemetry_state()
    assert state.commands == {}


def test_telemetry_records_events(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    set_telemetry_enabled(True)
    record_event("run", 0.2, None)
    record_event("run", 0.6, "ValueError")
    state = get_telemetry_state()
    assert state.commands["run"] == 2
    assert state.errors["ValueError"] == 1


def test_telemetry_context_records_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    set_telemetry_enabled(True)
    with pytest.raises(typer.Exit), telemetry_context("validate"):
        raise typer.Exit(code=1)
    state = get_telemetry_state()
    assert state.commands["validate"] == 1
    assert state.errors["typer.Exit"] == 1
