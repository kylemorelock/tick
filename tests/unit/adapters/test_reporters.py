from __future__ import annotations

from datetime import datetime, timezone

import msgspec

from tick.adapters.reporters.html import HtmlReporter
from tick.adapters.reporters.json import JsonReporter
from tick.adapters.reporters.markdown import MarkdownReporter
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session


def _make_session(checklist_id: str) -> Session:
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(timezone.utc),
        notes="ok",
        evidence=("screenshot.png",),
    )
    return Session(
        id="session-1",
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.COMPLETED,
        responses=[response],
        variables={},
    )


def test_html_reporter_outputs_content(minimal_checklist):
    reporter = HtmlReporter()
    session = _make_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    assert "Minimal Checklist" in output
    assert "item-1" in output


def test_markdown_reporter_outputs_table(minimal_checklist):
    reporter = MarkdownReporter()
    session = _make_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    assert "| ID | Check | Severity | Result | Notes |" in output
    assert "item-1" in output


def test_markdown_reporter_escapes_cells_and_matrix(minimal_checklist):
    reporter = MarkdownReporter()
    response = Response(
        item_id="item-1",
        result=ItemResult.FAIL,
        answered_at=datetime.now(timezone.utc),
        notes="line1\nline2 | note",
        matrix_context={"role": "admin"},
    )
    session = Session(
        id="session-2",
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.COMPLETED,
        responses=[response],
        variables={},
    )
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    assert "role=admin" in output
    assert "line1<br>line2 \\| note" in output


def test_json_reporter_emits_payload(minimal_checklist):
    reporter = JsonReporter()
    session = _make_session(minimal_checklist.checklist_id)
    data = reporter.generate(session, minimal_checklist)
    decoded = msgspec.json.decode(data)
    assert decoded["checklist"]["name"] == "Minimal Checklist"
    assert decoded["session"]["id"] == "session-1"
