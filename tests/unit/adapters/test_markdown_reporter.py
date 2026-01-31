from __future__ import annotations

from datetime import datetime, timezone

from tick.adapters.reporters.markdown import MarkdownReporter
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session


def test_markdown_reporter_escapes_cells(minimal_checklist) -> None:
    response = Response(
        item_id="item-1",
        result=ItemResult.FAIL,
        answered_at=datetime.now(timezone.utc),
        notes="needs | pipe\nand newline",
        evidence=(),
        matrix_context=None,
    )
    session = Session(
        id="b" * 32,
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        checklist_digest=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[response],
    )
    reporter = MarkdownReporter()
    content = reporter.generate(session, minimal_checklist).decode("utf-8")
    assert "\\|" in content
    assert "<br>" in content
