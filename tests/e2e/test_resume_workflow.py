"""E2E tests for resume workflow.

Tests the ability to pause and resume checklist execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tick.cli.app import app
from tick.cli.commands import run as run_module
from tick.core.models.enums import ItemResult
from tick.core.models.session import decode_session

if TYPE_CHECKING:
    from tests.e2e.conftest import AnswersFactory, ChecklistFactory
    from typer.testing import CliRunner


@pytest.mark.e2e
class TestResumeWorkflow:
    """Test session resume functionality."""

    def test_resume_continues_from_saved_state(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that resume continues from where the session left off."""
        checklist = checklist_file(
            """
checklist:
  name: "Resume Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First item"
        - id: "item-2"
          check: "Second item"
        - id: "item-3"
          check: "Third item"
"""
        )
        output_dir = tmp_path / "reports"

        monkeypatch.setattr(run_module, "ask_variables", lambda *args, **kwargs: {})

        # First run: answer only first item, then simulate interrupt
        call_count = [0]

        def first_run_responses(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return ItemResult.PASS, "First response", None
            # Simulate KeyboardInterrupt after first item
            raise KeyboardInterrupt()

        monkeypatch.setattr(run_module, "ask_item_response", first_run_responses)

        result1 = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        # KeyboardInterrupt should result in exit code 0 (graceful save)
        assert result1.exit_code == 0
        assert "Interrupted" in result1.stdout or "saved" in result1.stdout.lower()

        # Verify partial session exists
        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        assert len(session_files) == 1
        session = decode_session(session_files[0].read_bytes())
        assert session.status.value == "in_progress"
        assert len(session.responses) == 1

        # Resume run: answer remaining items
        resume_call_count = [0]

        def resume_responses(*args, **kwargs):
            resume_call_count[0] += 1
            return ItemResult.PASS, f"Resume response {resume_call_count[0]}", None

        monkeypatch.setattr(run_module, "ask_item_response", resume_responses)

        result2 = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir), "--resume"],
        )
        assert result2.exit_code == 0
        assert "Resuming" in result2.stdout

        # Verify completed session
        session = decode_session(session_files[0].read_bytes())
        assert session.status.value == "completed"
        assert len(session.responses) == 3
        # First response from initial run
        assert session.responses[0].notes == "First response"
        # Remaining from resume
        assert session.responses[1].notes == "Resume response 1"
        assert session.responses[2].notes == "Resume response 2"

    def test_resume_no_session_found_error(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test error when no in-progress session exists to resume."""
        checklist = checklist_file(
            """
checklist:
  name: "No Resume Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
"""
        )
        output_dir = tmp_path / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir), "--resume"],
        )
        assert result.exit_code == 1
        assert "No in-progress session found" in result.stdout

    def test_resume_cannot_combine_with_no_interactive(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that --resume cannot be used with --no-interactive."""
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

        result = cli_runner.invoke(
            app,
            [
                "run",
                str(checklist),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--no-interactive",
                "--answers",
                str(answers),
            ],
        )
        assert result.exit_code == 1
        assert "Resume cannot be combined" in result.stdout

    def test_resume_cannot_combine_with_dry_run(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
    ) -> None:
        """Test that --resume cannot be used with --dry-run."""
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
            ["run", str(checklist), "--resume", "--dry-run"],
        )
        assert result.exit_code == 1
        assert "Dry-run cannot be combined with --resume" in result.stdout


@pytest.mark.e2e
class TestResumeWithVariables:
    """Test resume with variable-driven checklists."""

    def test_resume_preserves_variables(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that resumed sessions use the originally recorded variables."""
        checklist = checklist_file(
            """
checklist:
  name: "Variables Resume Test"
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
          check: "First"
        - id: "item-2"
          check: "Second"
"""
        )
        output_dir = tmp_path / "reports"

        # First run with variables
        monkeypatch.setattr(run_module, "ask_variables", lambda *args, **kwargs: {"env": "dev"})

        call_count = [0]

        def first_run_responses(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return ItemResult.PASS, None, None
            raise KeyboardInterrupt()

        monkeypatch.setattr(run_module, "ask_item_response", first_run_responses)

        result1 = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        assert result1.exit_code == 0

        # Verify variables were saved
        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert session.variables["env"] == "dev"

        # Resume - variables should NOT be asked again
        variables_asked = [False]

        def should_not_be_called(*args, **kwargs):
            variables_asked[0] = True
            return {}

        monkeypatch.setattr(run_module, "ask_variables", should_not_be_called)
        monkeypatch.setattr(
            run_module,
            "ask_item_response",
            lambda *args, **kwargs: (ItemResult.PASS, None, None),
        )

        result2 = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir), "--resume"],
        )
        assert result2.exit_code == 0
        assert not variables_asked[0], "Variables should not be re-prompted on resume"

        # Verify variables preserved
        session = decode_session(session_files[0].read_bytes())
        assert session.variables["env"] == "dev"
