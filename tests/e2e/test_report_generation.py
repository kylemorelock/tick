"""E2E tests for report generation.

Tests generating reports in various formats from completed sessions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tick.cli.app import app

if TYPE_CHECKING:
    from tests.e2e.conftest import AnswersFactory, ChecklistFactory
    from typer.testing import CliRunner


def _run_checklist(
    cli_runner: CliRunner,
    checklist_path: Path,
    answers_path: Path,
    output_dir: Path,
) -> Path:
    """Run a checklist and return the session file path."""
    result = cli_runner.invoke(
        app,
        [
            "run",
            str(checklist_path),
            "--output-dir",
            str(output_dir),
            "--no-interactive",
            "--answers",
            str(answers_path),
        ],
    )
    assert result.exit_code == 0, f"Run failed: {result.stdout}"
    session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
    assert len(session_files) == 1
    return session_files[0]


@pytest.mark.e2e
class TestHtmlReportGeneration:
    """Test HTML report generation."""

    def test_html_report_basic(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test generating a basic HTML report."""
        checklist = checklist_file(
            """
checklist:
  name: "HTML Report Test"
  version: "1.0.0"
  domain: "test"
  metadata:
    author: "Test Author"
  sections:
    - name: "Main Section"
      items:
        - id: "item-1"
          check: "First check"
          severity: "high"
        - id: "item-2"
          check: "Second check"
          severity: "low"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
    notes: "Passed successfully"
  item-2:
    result: fail
    notes: "Found an issue"
"""
        )
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        # Generate HTML report
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "html",
                "--checklist",
                str(checklist),
            ],
        )
        assert result.exit_code == 0, f"Report failed: {result.stdout}"

        # Verify HTML file
        html_path = session_path.with_suffix(".html")
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")

        # Check key content
        assert "HTML Report Test" in html_content
        assert "First check" in html_content
        assert "Passed successfully" in html_content

    def test_html_report_includes_statistics(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that HTML report includes statistics."""
        checklist = checklist_file(
            """
checklist:
  name: "Stats Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check 1"
        - id: "item-2"
          check: "Check 2"
        - id: "item-3"
          check: "Check 3"
        - id: "item-4"
          check: "Check 4"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
  item-2:
    result: pass
  item-3:
    result: fail
  item-4:
    result: na
"""
        )
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "html",
                "--checklist",
                str(checklist),
            ],
        )
        assert result.exit_code == 0

        html_path = session_path.with_suffix(".html")
        html_content = html_path.read_text(encoding="utf-8")

        # Check for summary statistics (presence of the values)
        assert "summary-card pass" in html_content
        assert "summary-card fail" in html_content


@pytest.mark.e2e
class TestJsonReportGeneration:
    """Test JSON report generation."""

    def test_json_report_basic(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test generating a basic JSON report."""
        checklist = checklist_file(
            """
checklist:
  name: "JSON Report Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Test check"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
    notes: "All good"
"""
        )
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        # Generate JSON report to specific output path
        json_output = tmp_path / "report.json"
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "json",
                "--checklist",
                str(checklist),
                "--output",
                str(json_output),
            ],
        )
        assert result.exit_code == 0

        assert json_output.exists()
        data = json.loads(json_output.read_text(encoding="utf-8"))

        assert "checklist" in data
        assert data["checklist"]["name"] == "JSON Report Test"
        assert "session" in data
        assert "stats" in data

    def test_json_report_stats_correct(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that JSON report stats are accurate."""
        checklist = checklist_file(
            """
checklist:
  name: "Stats Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "i1"
          check: "Check"
        - id: "i2"
          check: "Check"
        - id: "i3"
          check: "Check"
"""
        )
        answers = answers_file(
            """
responses:
  i1:
    result: pass
  i2:
    result: fail
  i3:
    result: skip
"""
        )
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        json_output = tmp_path / "report.json"
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "json",
                "--checklist",
                str(checklist),
                "--output",
                str(json_output),
            ],
        )
        assert result.exit_code == 0

        data = json.loads(json_output.read_text(encoding="utf-8"))
        stats = data["stats"]
        assert stats["pass"] == 1
        assert stats["fail"] == 1
        assert stats["skip"] == 1
        assert stats["total"] == 3


@pytest.mark.e2e
class TestMarkdownReportGeneration:
    """Test Markdown report generation."""

    def test_markdown_report_basic(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test generating a basic Markdown report."""
        checklist = checklist_file(
            """
checklist:
  name: "Markdown Report Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Test Section"
      items:
        - id: "item-1"
          check: "Verify something"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
"""
        )
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "md",
                "--checklist",
                str(checklist),
            ],
        )
        assert result.exit_code == 0

        md_path = session_path.with_suffix(".md")
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")

        assert "# Markdown Report Test" in md_content
        assert "## Summary" in md_content
        assert "Verify something" in md_content  # Check content instead of section

    def test_markdown_alias_works(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that 'markdown' format alias works."""
        checklist = checklist_file(
            """
checklist:
  name: "Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        answers = answers_file("responses:\n  item-1:\n    result: pass")
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist, answers, output_dir)

        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "markdown",
                "--checklist",
                str(checklist),
            ],
        )
        assert result.exit_code == 0
        assert session_path.with_suffix(".md").exists()


@pytest.mark.e2e
class TestReportDigestValidation:
    """Test report generation validates session digest."""

    def test_report_rejects_modified_checklist(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that report generation fails if checklist was modified."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Original Name"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
""",
            encoding="utf-8",
        )
        answers = answers_file("responses:\n  item-1:\n    result: pass")
        output_dir = tmp_path / "reports"
        session_path = _run_checklist(cli_runner, checklist_path, answers, output_dir)

        # Modify the checklist after the session was created
        checklist_path.write_text(
            """
checklist:
  name: "Modified Name"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
""",
            encoding="utf-8",
        )

        # Try to generate report - should fail
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_path),
                "--format",
                "html",
                "--checklist",
                str(checklist_path),
            ],
        )
        assert result.exit_code == 1
        # Error message mentions checklist contents don't match
        assert "do not match" in result.stdout.lower() or "mismatch" in result.stdout.lower()
