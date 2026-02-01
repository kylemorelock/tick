from __future__ import annotations

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter, time

import msgspec
import typer


class TelemetryConfig(msgspec.Struct, frozen=True):
    enabled: bool
    updated_at: float


class TelemetryState(msgspec.Struct):
    commands: dict[str, int] = msgspec.field(default_factory=dict)
    duration_buckets: dict[str, int] = msgspec.field(default_factory=dict)
    errors: dict[str, int] = msgspec.field(default_factory=dict)
    last_event_at: float | None = None


def _config_dir() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "tick"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "tick"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "tick"
    return Path.home() / ".config" / "tick"


def _config_path() -> Path:
    return _config_dir() / "telemetry.json"


def _state_path() -> Path:
    return _config_dir() / "telemetry-state.json"


def _load_config() -> TelemetryConfig:
    path = _config_path()
    if not path.exists():
        return TelemetryConfig(enabled=False, updated_at=0.0)
    try:
        return msgspec.json.decode(path.read_bytes(), type=TelemetryConfig)
    except (OSError, msgspec.DecodeError, TypeError, ValueError):
        return TelemetryConfig(enabled=False, updated_at=0.0)


def _save_config(enabled: bool) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = TelemetryConfig(enabled=enabled, updated_at=time())
    try:
        path.write_bytes(msgspec.json.encode(payload))
    except OSError:
        return


def telemetry_enabled() -> bool:
    return _load_config().enabled


def set_telemetry_enabled(enabled: bool) -> None:
    _save_config(enabled)


def _load_state() -> TelemetryState:
    path = _state_path()
    if not path.exists():
        return TelemetryState()
    try:
        return msgspec.json.decode(path.read_bytes(), type=TelemetryState)
    except (OSError, msgspec.DecodeError, TypeError, ValueError):
        return TelemetryState()


def _save_state(state: TelemetryState) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(msgspec.json.encode(state))
    except OSError:
        return


def _bucket_duration(seconds: float) -> str:
    if seconds <= 0.1:
        return "lt_0_1s"
    if seconds <= 0.5:
        return "lt_0_5s"
    if seconds <= 1.0:
        return "lt_1s"
    if seconds <= 2.0:
        return "lt_2s"
    if seconds <= 5.0:
        return "lt_5s"
    if seconds <= 10.0:
        return "lt_10s"
    return "gte_10s"


def record_event(command: str, duration_seconds: float, error: str | None) -> None:
    if not telemetry_enabled():
        return
    state = _load_state()
    state.commands[command] = state.commands.get(command, 0) + 1
    bucket = _bucket_duration(duration_seconds)
    state.duration_buckets[bucket] = state.duration_buckets.get(bucket, 0) + 1
    if error:
        state.errors[error] = state.errors.get(error, 0) + 1
    state.last_event_at = time()
    _save_state(state)


def get_telemetry_state() -> TelemetryState:
    return _load_state()


@contextmanager
def telemetry_context(command: str) -> Generator[None, None, None]:
    start = perf_counter()
    try:
        yield
    except typer.Exit as exc:
        duration = perf_counter() - start
        if exc.exit_code == 0:
            record_event(command, duration, None)
        else:
            record_event(command, duration, "typer.Exit")
        raise
    except Exception as exc:  # pragma: no cover - defensive
        duration = perf_counter() - start
        record_event(command, duration, exc.__class__.__name__)
        raise
    else:
        duration = perf_counter() - start
        record_event(command, duration, None)
