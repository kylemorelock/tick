from __future__ import annotations

from datetime import UTC, datetime

import msgspec

from tick.adapters.reporters.html import HtmlReporter
from tick.adapters.reporters.json import JsonReporter
from tick.adapters.reporters.markdown import MarkdownReporter
from tick.adapters.reporters.stats import compute_stats
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session


def _make_session(checklist_id: str) -> Session:
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
        notes="ok",
        evidence=("screenshot.png",),
    )
    return Session(
        id="session-1",
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[response],
        variables={},
    )


def _make_multi_result_session(checklist_id: str) -> Session:
    """Create a session with multiple result types for stats testing."""
    responses = [
        Response(item_id="item-1", result=ItemResult.PASS, answered_at=datetime.now(UTC)),
        Response(item_id="item-2", result=ItemResult.PASS, answered_at=datetime.now(UTC)),
        Response(item_id="item-3", result=ItemResult.FAIL, answered_at=datetime.now(UTC)),
        Response(item_id="item-4", result=ItemResult.SKIP, answered_at=datetime.now(UTC)),
        Response(item_id="item-5", result=ItemResult.NOT_APPLICABLE, answered_at=datetime.now(UTC)),
    ]
    return Session(
        id="session-stats",
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=responses,
        variables={"environment": "prod"},
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
        answered_at=datetime.now(UTC),
        notes="line1\nline2 | note",
        matrix_context={"role": "admin"},
    )
    session = Session(
        id="session-2",
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        started_at=datetime.now(UTC),
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


def test_compute_stats_counts_results():
    """Verify compute_stats correctly counts each result type."""
    responses = [
        Response(item_id="a", result=ItemResult.PASS, answered_at=datetime.now(UTC)),
        Response(item_id="b", result=ItemResult.PASS, answered_at=datetime.now(UTC)),
        Response(item_id="c", result=ItemResult.FAIL, answered_at=datetime.now(UTC)),
        Response(item_id="d", result=ItemResult.SKIP, answered_at=datetime.now(UTC)),
        Response(item_id="e", result=ItemResult.NOT_APPLICABLE, answered_at=datetime.now(UTC)),
    ]
    stats = compute_stats(responses)
    assert stats["pass"] == 2
    assert stats["fail"] == 1
    assert stats["skip"] == 1
    assert stats["na"] == 1
    assert stats["total"] == 5


def test_compute_stats_empty_responses():
    """Verify compute_stats handles empty response list."""
    stats = compute_stats([])
    assert stats["pass"] == 0
    assert stats["fail"] == 0
    assert stats["skip"] == 0
    assert stats["na"] == 0
    assert stats["total"] == 0


def test_html_reporter_includes_stats(minimal_checklist):
    """Verify HTML report includes summary statistics section."""
    reporter = HtmlReporter()
    session = _make_multi_result_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    # Check for summary section with stats
    assert "summary-card pass" in output
    assert "summary-card fail" in output
    assert "summary-card skip" in output
    # Check counts are present
    assert ">2<" in output  # 2 passes
    assert ">1<" in output  # 1 fail, 1 skip, 1 na


def test_html_reporter_includes_variables(minimal_checklist):
    """Verify HTML report includes variables section when present."""
    reporter = HtmlReporter()
    session = _make_multi_result_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    assert "environment" in output
    assert "prod" in output


def test_html_reporter_includes_styled_results(minimal_checklist):
    """Verify HTML report includes color-coded result badges."""
    reporter = HtmlReporter()
    session = _make_multi_result_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    # Check for result badge classes
    assert 'class="result pass"' in output
    assert 'class="result fail"' in output
    assert 'class="result skip"' in output
    assert 'class="result na"' in output


def test_markdown_reporter_includes_stats(minimal_checklist):
    """Verify markdown report includes summary statistics."""
    reporter = MarkdownReporter()
    session = _make_multi_result_session(minimal_checklist.checklist_id)
    output = reporter.generate(session, minimal_checklist).decode("utf-8")
    # Check for summary section
    assert "## Summary" in output
    assert "**Pass**: 2" in output
    assert "**Fail**: 1" in output
    assert "**Skip**: 1" in output
    assert "**N/A**: 1" in output
    assert "**Total**: 5" in output


def test_json_reporter_includes_stats(minimal_checklist):
    """Verify JSON report includes summary statistics."""
    reporter = JsonReporter()
    session = _make_multi_result_session(minimal_checklist.checklist_id)
    data = reporter.generate(session, minimal_checklist)
    decoded = msgspec.json.decode(data)
    assert "stats" in decoded
    assert decoded["stats"]["pass"] == 2
    assert decoded["stats"]["fail"] == 1
    assert decoded["stats"]["skip"] == 1
    assert decoded["stats"]["na"] == 1
    assert decoded["stats"]["total"] == 5
