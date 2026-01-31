from __future__ import annotations

import runpy
import sys

import pytest

from tick import __main__


def test_main_invokes_app(monkeypatch):
    called = {"value": False}

    def fake_app():
        called["value"] = True
        return 0

    import tick.cli.app as app_module

    monkeypatch.setattr(app_module, "app", fake_app)
    result = __main__.main()
    assert result == 0
    assert called["value"] is True


def test_main_module_execution(monkeypatch):
    import tick.cli.app as app_module

    monkeypatch.setattr(app_module, "app", lambda: 0)
    sys.modules.pop("tick.__main__", None)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tick.__main__", run_name="__main__")
    assert exc.value.code == 0
