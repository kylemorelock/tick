"""E2E tests for error scenarios.

Tests error handling and edge cases in the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tick.cli.app import app

if TYPE_CHECKING:
    from tests.e2e.conftest import AnswersFactory, ChecklistFactory
    from typer.testing import CliRunner


@pytest.mark.e2e
class TestInvalidChecklist:
    """Test error handling for invalid checklists."""

    def test_run_with_missing_checklist_file(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Test error when checklist file doesn't exist."""
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(tmp_path / "nonexistent.yaml"),
                "--output-dir",
                str(tmp_path / "reports"),
            ],
        )
        # Exit code 2 = Typer usage error (file doesn't exist)
        # Exit code 1 = Application error
        assert result.exit_code in (1, 2)
        # Error appears in output (stdout + stderr combined)
        output = result.output.lower()
        assert "nonexistent" in output or "invalid value" in output or "does not exist" in output

    def test_run_with_invalid_yaml(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test error when YAML is malformed."""
        checklist = checklist_file(
            """
checklist:
  name: "Test
  version: "1.0.0"
"""
        )
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
            ],
        )
        assert result.exit_code == 1
        # Check output or exception info
        output = result.output.lower()
        assert "failed to load" in output or "error" in output or result.exception is not None

    def test_run_with_invalid_schema(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test error when checklist doesn't match schema."""
        checklist = checklist_file(
            """
checklist:
  name: "Invalid"
  # Missing required fields: version, domain, sections
"""
        )
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
            ],
        )
        assert result.exit_code == 1
        assert "Failed to load checklist" in result.stdout or "validation" in result.stdout.lower()

    def test_validate_invalid_checklist(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test validate command with invalid checklist."""
        checklist = checklist_file(
            """
checklist:
  name: "Incomplete"
  version: "1.0.0"
  # Missing domain and sections
"""
        )
        result = cli_runner.invoke(
            app,
            ["validate", str(checklist)],
        )
        assert result.exit_code == 1


@pytest.mark.e2e
class TestInvalidAnswersFile:
    """Test error handling for invalid answers files."""

    def test_noninteractive_with_missing_answers(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test error when answers file doesn't exist."""
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
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
                "--no-interactive",
                "--answers",
                str(tmp_path / "nonexistent.yaml"),
            ],
        )
        # Exit code 2 = Typer validation, 1 = app error
        assert result.exit_code in (1, 2)
        # Error appears in output (stdout + stderr combined)
        output = result.output.lower()
        assert "nonexistent" in output or "invalid value" in output or "does not exist" in output

    def test_noninteractive_with_invalid_answers_yaml(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test error when answers YAML is malformed."""
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
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
    notes: "Missing closing quote
"""
        )
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        assert result.exit_code == 1

    def test_noninteractive_missing_required_variable(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test error when required variable is missing."""
        checklist = checklist_file(
            """
checklist:
  name: "Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      required: true
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        answers = answers_file(
            """
# Missing variables section
responses:
  item-1:
    result: pass
"""
        )
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        assert result.exit_code == 1
        assert "Missing required variable" in result.stdout

    def test_noninteractive_invalid_variable_option(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test error when variable value not in allowed options."""
        checklist = checklist_file(
            """
checklist:
  name: "Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        answers = answers_file(
            """
variables:
  env: invalid_option
responses:
  item-1:
    result: pass
"""
        )
        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(tmp_path / "reports"),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        assert result.exit_code == 1
        assert "Invalid value" in result.stdout


@pytest.mark.e2e
class TestReportErrors:
    """Test error handling in report generation."""

    def test_report_with_missing_session_file(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Test error when session file doesn't exist."""
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(tmp_path / "session-nonexistent.json"),
                "--format",
                "html",
            ],
        )
        # Exit code 2 = Typer validation error, 1 = app error
        assert result.exit_code in (1, 2)

    def test_report_with_invalid_session_format(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Test error when session file has invalid name format."""
        bad_session = tmp_path / "not-a-session.json"
        bad_session.write_text("{}", encoding="utf-8")

        result = cli_runner.invoke(
            app,
            [
                "report",
                str(bad_session),
                "--format",
                "html",
            ],
        )
        assert result.exit_code == 1

    def test_report_invalid_format(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test error for unsupported report format."""
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

        # Run first to create session
        cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(output_dir),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]

        # Try invalid format
        result = cli_runner.invoke(
            app,
            [
                "report",
                str(session_files[0]),
                "--format",
                "pdf",  # Not supported
                "--checklist",
                str(checklist),
            ],
        )
        assert result.exit_code != 0


@pytest.mark.e2e
class TestDryRunErrors:
    """Test error handling in dry-run mode."""

    def test_dry_run_with_missing_checklist(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Test dry-run error when checklist doesn't exist."""
        result = cli_runner.invoke(
            app,
            ["run", str(tmp_path / "missing.yaml"), "--dry-run"],
        )
        # Exit code 2 = Typer validation error, 1 = app error
        assert result.exit_code in (1, 2)


@pytest.mark.e2e
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_checklist_sections(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test checklist with empty sections list."""
        checklist = checklist_file(
            """
checklist:
  name: "Empty"
  version: "1.0.0"
  domain: "test"
  sections: []
"""
        )
        output_dir = tmp_path / "reports"

        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(output_dir),
                "--no-interactive",
            ],
        )
        # Empty checklist should complete successfully
        assert result.exit_code == 0

    def test_all_items_conditionally_excluded(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test when all items are excluded by conditions."""
        checklist = checklist_file(
            """
checklist:
  name: "All Excluded"
  version: "1.0.0"
  domain: "test"
  variables:
    show:
      prompt: "Show items?"
      options: ["yes", "no"]
      required: true
  sections:
    - name: "Conditional"
      condition: "show == 'yes'"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        answers = answers_file(
            """
variables:
  show: "no"
"""
        )
        output_dir = tmp_path / "reports"

        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(output_dir),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        # Should complete with 0 items
        assert result.exit_code == 0

    def test_unused_answers_warning(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test warning when answers file has unused entries."""
        checklist = checklist_file(
            """
checklist:
  name: "Unused Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
  nonexistent-item:
    result: fail
  another-unused:
    result: skip
"""
        )
        output_dir = tmp_path / "reports"

        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(output_dir),
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        assert result.exit_code == 0
        assert "Warning" in result.stdout
        assert "2" in result.stdout  # 2 unused entries
