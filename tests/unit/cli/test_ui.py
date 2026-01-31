from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console
from rich.prompt import Confirm, Prompt

from tick.cli.ui.progress import run_progress
from tick.cli.ui.prompts import ask_item_response, ask_variables
from tick.cli.ui.tables import render_summary
from tick.core.models.checklist import ChecklistItem, ChecklistVariable
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session
from tick.core.state import ResolvedItem


def test_ask_variables_with_required_and_options(monkeypatch):
    responses = ["", "dev", "on"]

    def fake_prompt(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", staticmethod(fake_prompt))
    variables = {
        "environment": ChecklistVariable(
            prompt="Environment",
            required=True,
            options=["dev", "prod"],
        ),
        "feature_flag": ChecklistVariable(prompt="Feature", default="on"),
    }
    console = Console()
    result = ask_variables(variables, console)
    assert result["environment"] == "dev"
    assert result["feature_flag"] == "on"


def test_ask_item_response_collects_evidence(monkeypatch):
    responses = ["fail", "Needs work", "log.txt, screenshot.png"]

    def fake_prompt(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", staticmethod(fake_prompt))
    monkeypatch.setattr(Confirm, "ask", staticmethod(lambda *args, **kwargs: True))

    item = ChecklistItem(id="item-1", check="Check login", guidance="Try invalid user")
    resolved = ResolvedItem(section_name="Auth", item=item)
    console = Console()
    result, notes, evidence = ask_item_response(resolved, console)
    assert result == ItemResult.FAIL
    assert notes == "Needs work"
    assert list(evidence) == ["log.txt", "screenshot.png"]


def test_ask_variables_skips_none(monkeypatch):
    monkeypatch.setattr(Prompt, "ask", staticmethod(lambda *args, **kwargs: None))
    variables = {
        "optional": ChecklistVariable(prompt="Optional"),
    }
    console = Console()
    result = ask_variables(variables, console)
    assert "optional" not in result


def test_ask_variables_required_without_options(monkeypatch):
    responses = ["", "value"]

    def fake_prompt(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", staticmethod(fake_prompt))
    variables = {
        "name": ChecklistVariable(prompt="Name", required=True),
    }
    console = Console()
    result = ask_variables(variables, console)
    assert result["name"] == "value"


def test_ask_item_response_without_guidance_or_evidence(monkeypatch):
    responses = ["pass", ""]

    def fake_prompt(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", staticmethod(fake_prompt))
    monkeypatch.setattr(Confirm, "ask", staticmethod(lambda *args, **kwargs: False))

    item = ChecklistItem(id="item-2", check="Check logout")
    resolved = ResolvedItem(section_name="Auth", item=item)
    console = Console()
    result, notes, evidence = ask_item_response(resolved, console)
    assert result == ItemResult.PASS
    assert notes is None
    assert list(evidence) == []


def test_ask_item_response_reprompts_on_invalid(monkeypatch):
    responses = ["bad", "p", ""]

    def fake_prompt(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", staticmethod(fake_prompt))
    monkeypatch.setattr(Confirm, "ask", staticmethod(lambda *args, **kwargs: False))

    item = ChecklistItem(id="item-3", check="Check profile")
    resolved = ResolvedItem(section_name="Profile", item=item)
    console = Console(record=True)
    result, notes, evidence = ask_item_response(resolved, console)
    output = console.export_text()
    assert "Please enter one of" in output
    assert result == ItemResult.PASS
    assert notes is None
    assert list(evidence) == []


def test_render_summary_outputs_table():
    console = Console(record=True)
    session = Session(
        id="session-1",
        checklist_id="checklist-1",
        checklist_path=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[
            Response(
                item_id="item-1",
                result=ItemResult.PASS,
                answered_at=datetime.now(UTC),
            )
        ],
        variables={},
    )
    render_summary(session, console)
    output = console.export_text()
    assert "Checklist Summary" in output


def test_run_progress_creates_task():
    console = Console()
    progress = run_progress(total=3, console=console)
    assert len(progress.tasks) == 1
