from __future__ import annotations

from tick.cli.commands import templates as templates_module


class DummyRoot:
    def iterdir(self):
        return []


def test_templates_command_no_templates(monkeypatch):
    monkeypatch.setattr(templates_module, "template_keys", lambda: [])
    templates_module.templates_command()
