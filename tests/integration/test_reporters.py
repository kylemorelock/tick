"""Integration tests for reporters.

Tests reporter output generation from real session data.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from tick.adapters.reporters.html import HtmlReporter
from tick.adapters.reporters.json import JsonReporter
from tick.adapters.reporters.markdown import MarkdownReporter
from tick.core.models.checklist import Checklist, ChecklistItem, ChecklistSection
from tick.core.models.enums import ItemResult, SessionStatus, Severity
from tick.core.models.session import Response, Session


def _make_session(checklist: Checklist, responses: list[Response]) -> Session:
    """Create a session for testing."""
    return Session(
        id="test-session-id-12345678901234",
        checklist_id=checklist.checklist_id,
        checklist_path="checklist.yaml",
        started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        status=SessionStatus.COMPLETED,
        variables={"env": "prod"},
        responses=responses,
    )


def _make_checklist() -> Checklist:
    """Create a test checklist."""
    return Checklist(
        name="Reporter Test Checklist",
        version="1.0.0",
        domain="test",
        sections=[
            ChecklistSection(
                name="Security Checks",
                items=[
                    ChecklistItem(
                        id="sec-1",
                        check="Verify SSL certificate",
                        severity=Severity.CRITICAL,
                        guidance="Check expiration date",
                        evidence_required=True,
                    ),
                    ChecklistItem(
                        id="sec-2",
                        check="Check firewall rules",
                        severity=Severity.HIGH,
                    ),
                ],
            ),
            ChecklistSection(
                name="Performance Checks",
                items=[
                    ChecklistItem(
                        id="perf-1",
                        check="Verify response times",
                    ),
                ],
            ),
        ],
    )


def _make_responses() -> list[Response]:
    """Create test responses."""
    return [
        Response(
            item_id="sec-1",
            result=ItemResult.PASS,
            answered_at=datetime(2024, 1, 15, 10, 10, 0, tzinfo=UTC),
            notes="Certificate valid until 2025",
            evidence=("cert-check.log", "screenshot.png"),
            matrix_context=None,
        ),
        Response(
            item_id="sec-2",
            result=ItemResult.FAIL,
            answered_at=datetime(2024, 1, 15, 10, 15, 0, tzinfo=UTC),
            notes="Found open port 22",
            evidence=(),  # Empty tuple instead of None
            matrix_context=None,
        ),
        Response(
            item_id="perf-1",
            result=ItemResult.NOT_APPLICABLE,
            answered_at=datetime(2024, 1, 15, 10, 20, 0, tzinfo=UTC),
            notes="Not tested in this environment",
            evidence=(),  # Empty tuple instead of None
            matrix_context=None,
        ),
    ]


@pytest.mark.integration
class TestHtmlReporter:
    """Test HTML report generation."""

    def test_html_report_contains_checklist_info(self) -> None:
        """Test that HTML report includes checklist metadata."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = HtmlReporter()
        html_bytes = reporter.generate(session, checklist)
        html = html_bytes.decode("utf-8")

        assert "Reporter Test Checklist" in html
        assert "1.0.0" in html
        assert "test" in html  # domain

    def test_html_report_contains_all_responses(self) -> None:
        """Test that HTML report includes all response data."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = HtmlReporter()
        html = reporter.generate(session, checklist).decode("utf-8")

        # Check items are present
        assert "sec-1" in html
        assert "sec-2" in html
        assert "perf-1" in html

        # Check notes are present
        assert "Certificate valid until 2025" in html
        assert "Found open port 22" in html

        # Check evidence is present
        assert "cert-check.log" in html

    def test_html_report_includes_statistics(self) -> None:
        """Test that HTML report includes summary statistics."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = HtmlReporter()
        html = reporter.generate(session, checklist).decode("utf-8")

        # Should have pass/fail/na counts
        assert "summary-card pass" in html
        assert "summary-card fail" in html

    def test_html_reporter_properties(self) -> None:
        """Test reporter interface properties."""
        reporter = HtmlReporter()
        assert reporter.content_type == "text/html"
        assert reporter.file_extension == "html"


@pytest.mark.integration
class TestJsonReporter:
    """Test JSON report generation."""

    def test_json_report_structure(self) -> None:
        """Test that JSON report has correct structure."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = JsonReporter()
        json_bytes = reporter.generate(session, checklist)
        data = json.loads(json_bytes)

        assert "checklist" in data
        assert "session" in data
        assert "stats" in data
        # Responses are inside session
        assert "responses" in data["session"]

    def test_json_report_stats_are_accurate(self) -> None:
        """Test that JSON stats are computed correctly."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = JsonReporter()
        data = json.loads(reporter.generate(session, checklist))

        stats = data["stats"]
        assert stats["pass"] == 1
        assert stats["fail"] == 1
        assert stats["skip"] == 0
        assert stats["na"] == 1
        assert stats["total"] == 3

    def test_json_report_preserves_evidence(self) -> None:
        """Test that evidence is preserved in JSON output."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = JsonReporter()
        data = json.loads(reporter.generate(session, checklist))

        # Responses in session are msgspec-serialized (list format)
        # First response should be sec-1 with evidence
        session_responses = data["session"]["responses"]
        # sec-1 is first response - evidence is at index 4
        assert "cert-check.log" in session_responses[0][4]
        assert "screenshot.png" in session_responses[0][4]

    def test_json_reporter_properties(self) -> None:
        """Test reporter interface properties."""
        reporter = JsonReporter()
        assert reporter.content_type == "application/json"
        assert reporter.file_extension == "json"


@pytest.mark.integration
class TestMarkdownReporter:
    """Test Markdown report generation."""

    def test_markdown_report_structure(self) -> None:
        """Test that Markdown report has correct structure."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = MarkdownReporter()
        md = reporter.generate(session, checklist).decode("utf-8")

        assert "# Reporter Test Checklist" in md
        assert "## Summary" in md
        assert "## Results" in md

    def test_markdown_report_includes_table(self) -> None:
        """Test that Markdown report includes results table."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = MarkdownReporter()
        md = reporter.generate(session, checklist).decode("utf-8")

        # Table headers
        assert "| ID |" in md
        assert "| Check |" in md
        assert "| Result |" in md

        # Table data
        assert "| sec-1 |" in md
        assert "| pass |" in md
        assert "| fail |" in md

    def test_markdown_report_stats(self) -> None:
        """Test that Markdown report includes statistics."""
        checklist = _make_checklist()
        responses = _make_responses()
        session = _make_session(checklist, responses)

        reporter = MarkdownReporter()
        md = reporter.generate(session, checklist).decode("utf-8")

        assert "**Pass**: 1" in md
        assert "**Fail**: 1" in md
        assert "**N/A**: 1" in md

    def test_markdown_reporter_properties(self) -> None:
        """Test reporter interface properties."""
        reporter = MarkdownReporter()
        assert reporter.content_type == "text/markdown"
        assert reporter.file_extension == "md"


@pytest.mark.integration
class TestReporterWithMatrixItems:
    """Test reporters handle matrix items correctly."""

    def test_reporters_handle_matrix_context(self) -> None:
        """Test that reporters display matrix context."""
        checklist = Checklist(
            name="Matrix Test",
            version="1.0.0",
            domain="test",
            sections=[
                ChecklistSection(
                    name="Browser Tests",
                    items=[
                        ChecklistItem(
                            id="browser-test",
                            check="Test functionality",
                            matrix=[
                                {"browser": "chrome"},
                                {"browser": "firefox"},
                            ],
                        ),
                    ],
                ),
            ],
        )

        responses = [
            Response(
                item_id="browser-test",
                result=ItemResult.PASS,
                answered_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
                notes="Chrome works",
                evidence=None,
                matrix_context={"browser": "chrome"},
            ),
            Response(
                item_id="browser-test",
                result=ItemResult.FAIL,
                answered_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC),
                notes="Firefox fails",
                evidence=None,
                matrix_context={"browser": "firefox"},
            ),
        ]

        session = _make_session(checklist, responses)

        # JSON should include matrix context
        json_reporter = JsonReporter()
        json_data = json.loads(json_reporter.generate(session, checklist))

        # Responses are msgspec-serialized in session
        session_responses = json_data["session"]["responses"]
        # First response should be chrome (pass), second is firefox (fail)
        # Result is at index 1 in the tuple format
        assert session_responses[0][1] == "pass"  # chrome
        assert session_responses[1][1] == "fail"  # firefox
