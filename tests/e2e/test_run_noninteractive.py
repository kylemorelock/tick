"""E2E tests for non-interactive run workflows.

Tests batch execution with answers files.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tick.cli.app import app
from tick.core.models.session import decode_session

if TYPE_CHECKING:
    from tests.e2e.conftest import AnswersFactory, ChecklistFactory
    from typer.testing import CliRunner


@pytest.mark.e2e
class TestNonInteractiveRun:
    """Test non-interactive batch execution."""

    def test_noninteractive_run_basic(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test basic non-interactive run with all answers provided."""
        checklist = checklist_file(
            """
checklist:
  name: "Batch Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First check"
        - id: "item-2"
          check: "Second check"
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
    notes: "Item 1 passed"
  item-2:
    result: fail
    notes: "Item 2 failed"
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
        assert result.exit_code == 0, f"Failed: {result.stdout}"

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        assert len(session_files) == 1

        session = decode_session(session_files[0].read_bytes())
        assert session.status.value == "completed"
        assert len(session.responses) == 2
        assert session.responses[0].result.value == "pass"
        assert session.responses[0].notes == "Item 1 passed"
        assert session.responses[1].result.value == "fail"

    def test_noninteractive_with_variables(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test non-interactive run with variables in answers file."""
        checklist = checklist_file(
            """
checklist:
  name: "Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "staging", "prod"]
      required: true
  sections:
    - name: "Main"
      items:
        - id: "check-1"
          check: "Environment check"
"""
        )
        answers = answers_file(
            """
variables:
  env: staging
responses:
  check-1:
    result: pass
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

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert session.variables["env"] == "staging"

    def test_noninteractive_missing_answers_default_skip(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that missing responses default to skip."""
        checklist = checklist_file(
            """
checklist:
  name: "Skip Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Has answer"
        - id: "item-2"
          check: "No answer provided"
        - id: "item-3"
          check: "Also no answer"
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

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert len(session.responses) == 3
        assert session.responses[0].result.value == "pass"
        assert session.responses[1].result.value == "skip"
        assert session.responses[2].result.value == "skip"

    def test_noninteractive_with_evidence(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test evidence is properly recorded from answers file."""
        checklist = checklist_file(
            """
checklist:
  name: "Evidence Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check with evidence"
          evidence_required: true
"""
        )
        answers = answers_file(
            """
responses:
  item-1:
    result: pass
    evidence: "screenshot.png, log.txt, video.mp4"
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

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        evidence = session.responses[0].evidence
        assert "screenshot.png" in evidence
        assert "log.txt" in evidence
        assert "video.mp4" in evidence


@pytest.mark.e2e
class TestNonInteractiveMatrix:
    """Test non-interactive mode with matrix items."""

    def test_noninteractive_matrix_with_explicit_context(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test providing different answers for each matrix expansion."""
        checklist = checklist_file(
            """
checklist:
  name: "Matrix Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Browsers"
      items:
        - id: "browser-check"
          check: "Test browser"
          matrix:
            - browser: "chrome"
            - browser: "firefox"
"""
        )
        # Use list format to specify matrix context
        answers = answers_file(
            """
responses:
  - item_id: browser-check
    matrix:
      browser: chrome
    result: pass
    notes: "Chrome works great"
  - item_id: browser-check
    matrix:
      browser: firefox
    result: fail
    notes: "Firefox has issues"
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

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert len(session.responses) == 2

        # Find each response by matrix context
        chrome_response = next(
            r for r in session.responses if r.matrix_context.get("browser") == "chrome"
        )
        firefox_response = next(
            r for r in session.responses if r.matrix_context.get("browser") == "firefox"
        )

        assert chrome_response.result.value == "pass"
        assert firefox_response.result.value == "fail"


@pytest.mark.e2e
class TestNonInteractiveConditions:
    """Test non-interactive mode with conditional sections/items."""

    def test_conditions_filter_items_based_on_variables(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that conditions correctly filter items based on variables."""
        checklist = checklist_file(
            """
checklist:
  name: "Conditional Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Always"
      items:
        - id: "always-1"
          check: "This always runs"
    - name: "Dev Only"
      condition: "env == 'dev'"
      items:
        - id: "dev-1"
          check: "Dev-only check"
"""
        )

        # Test with env=dev - should have 2 items
        answers_dev = answers_file(
            """
variables:
  env: dev
responses:
  always-1:
    result: pass
  dev-1:
    result: pass
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
                str(answers_dev),
            ],
        )
        assert result.exit_code == 0

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert len(session.responses) == 2
        item_ids = [r.item_id for r in session.responses]
        assert "always-1" in item_ids
        assert "dev-1" in item_ids

    def test_conditions_exclude_items_in_prod(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        answers_file: AnswersFactory,
    ) -> None:
        """Test that prod environment excludes dev-only items."""
        checklist = checklist_file(
            """
checklist:
  name: "Conditional Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Always"
      items:
        - id: "always-1"
          check: "This always runs"
    - name: "Dev Only"
      condition: "env == 'dev'"
      items:
        - id: "dev-1"
          check: "Dev-only check"
"""
        )

        # Test with env=prod - should only have 1 item
        answers_prod = answers_file(
            """
variables:
  env: prod
responses:
  always-1:
    result: pass
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
                str(answers_prod),
            ],
        )
        assert result.exit_code == 0

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert len(session.responses) == 1
        assert session.responses[0].item_id == "always-1"
