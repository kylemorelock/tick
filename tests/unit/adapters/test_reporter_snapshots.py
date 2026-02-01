from __future__ import annotations

from datetime import UTC, datetime

from tick.adapters.reporters.html import HtmlReporter
from tick.adapters.reporters.markdown import MarkdownReporter
from tick.core.models.checklist import ChecklistDocument
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session

FIXED_TIME = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


def _two_item_checklist():
    raw = {
        "checklist": {
            "name": "Two Item Checklist",
            "version": "1.0.0",
            "domain": "web",
            "sections": [
                {
                    "name": "Basics",
                    "items": [
                        {"id": "item-1", "check": "First item"},
                        {"id": "item-2", "check": "Second item"},
                    ],
                }
            ],
        }
    }
    return ChecklistDocument.from_raw(raw).checklist


def _snapshot_session(checklist_id: str) -> Session:
    return Session(
        id="session-snapshot",
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=FIXED_TIME,
        completed_at=FIXED_TIME,
        status=SessionStatus.COMPLETED,
        responses=[
            Response(
                item_id="item-2",
                result=ItemResult.FAIL,
                answered_at=FIXED_TIME,
                notes="oops",
            ),
            Response(
                item_id="item-1",
                result=ItemResult.PASS,
                answered_at=FIXED_TIME,
                notes="ok",
            ),
        ],
        variables={},
    )


def test_html_report_snapshot(snapshot):
    checklist = _two_item_checklist()
    session = _snapshot_session(checklist.checklist_id)
    reporter = HtmlReporter()
    output = reporter.generate(session, checklist).decode("utf-8")
    assert output == snapshot


def test_markdown_report_snapshot(snapshot):
    checklist = _two_item_checklist()
    session = _snapshot_session(checklist.checklist_id)
    reporter = MarkdownReporter()
    output = reporter.generate(session, checklist).decode("utf-8")
    assert output == snapshot
