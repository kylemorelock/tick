"""E2E tests for interactive run workflows.

Tests the complete interactive experience with simulated user input.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from tick.cli.app import app
from tick.cli.commands import run as run_module
from tick.core.models.enums import ItemResult
from tick.core.models.session import decode_session

if TYPE_CHECKING:
    from tests.e2e.conftest import ChecklistFactory


@pytest.mark.e2e
class TestInteractiveRun:
    """Test interactive run workflows with simulated input."""

    def test_interactive_run_with_monkeypatched_prompts(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test interactive mode with simulated user input via monkeypatch."""
        checklist = checklist_file(
            """
checklist:
  name: "Interactive Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Test item"
"""
        )
        output_dir = tmp_path / "reports"

        # Patch where the functions are imported (in run module)
        monkeypatch.setattr(run_module, "ask_variables", lambda *args, **kwargs: {})

        call_count = [0]

        def mock_ask_item_response(*args, **kwargs):
            call_count[0] += 1
            return ItemResult.PASS, "Test notes", ["evidence.txt"]

        monkeypatch.setattr(run_module, "ask_item_response", mock_ask_item_response)

        result = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        assert result.exit_code == 0, f"Failed: {result.stdout}"
        assert call_count[0] == 1  # One item in checklist

        # Verify session was created
        session_files = list(output_dir.glob("session-*.json"))
        session_files = [f for f in session_files if "index" not in f.name]
        assert len(session_files) == 1

        session = decode_session(session_files[0].read_bytes())
        assert session.status.value == "completed"
        assert len(session.responses) == 1
        assert session.responses[0].result.value == "pass"

    def test_interactive_run_with_variables(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test interactive mode prompts for variables before items."""
        checklist = checklist_file(
            """
checklist:
  name: "Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Main"
      items:
        - id: "item-1"
          check: "Check it"
"""
        )
        output_dir = tmp_path / "reports"

        variables_asked = [False]

        def mock_ask_variables(specs, console):
            variables_asked[0] = True
            return {"env": "dev"}

        monkeypatch.setattr(run_module, "ask_variables", mock_ask_variables)
        monkeypatch.setattr(
            run_module,
            "ask_item_response",
            lambda *args, **kwargs: (ItemResult.PASS, None, None),
        )

        result = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert variables_asked[0], "Variables should be prompted in interactive mode"

        # Verify variable was recorded
        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert session.variables["env"] == "dev"

    def test_interactive_run_go_back_navigation(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that users can go back to previous items."""
        checklist = checklist_file(
            """
checklist:
  name: "Back Navigation Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First item"
        - id: "item-2"
          check: "Second item"
"""
        )
        output_dir = tmp_path / "reports"

        monkeypatch.setattr(run_module, "ask_variables", lambda *args, **kwargs: {})

        # Sequence: pass item-1, go back (None), pass item-1 again, pass item-2
        responses = iter(
            [
                (ItemResult.PASS, "First answer", None),
                (None, None, None),  # Go back
                (ItemResult.FAIL, "Changed answer", None),  # Re-answer item-1
                (ItemResult.PASS, "Second answer", None),
            ]
        )

        def mock_ask_item_response(*args, **kwargs):
            return next(responses)

        monkeypatch.setattr(run_module, "ask_item_response", mock_ask_item_response)

        result = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        assert result.exit_code == 0

        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())

        # Verify final answers
        assert len(session.responses) == 2
        assert session.responses[0].result.value == "fail"  # Changed answer
        assert session.responses[1].result.value == "pass"


@pytest.mark.e2e
class TestInteractiveWithMatrix:
    """Test interactive mode with matrix-expanded items."""

    def test_interactive_run_expands_matrix_items(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
        checklist_file: ChecklistFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that matrix items are expanded and each is prompted."""
        checklist = checklist_file(
            """
checklist:
  name: "Matrix Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Browser Tests"
      items:
        - id: "browser-check"
          check: "Test browser"
          matrix:
            - browser: "chrome"
            - browser: "firefox"
"""
        )
        output_dir = tmp_path / "reports"

        monkeypatch.setattr(run_module, "ask_variables", lambda *args, **kwargs: {})

        items_seen = []

        def mock_ask_item_response(item, console, can_go_back=False):
            items_seen.append(item.matrix_context)
            return ItemResult.PASS, None, None

        monkeypatch.setattr(run_module, "ask_item_response", mock_ask_item_response)

        result = cli_runner.invoke(
            app,
            ["run", str(checklist), "--output-dir", str(output_dir)],
        )
        assert result.exit_code == 0

        # Two matrix expansions
        assert len(items_seen) == 2
        browsers = [ctx["browser"] for ctx in items_seen]
        assert "chrome" in browsers
        assert "firefox" in browsers

        # Verify session
        session_files = [f for f in output_dir.glob("session-*.json") if "index" not in f.name]
        session = decode_session(session_files[0].read_bytes())
        assert len(session.responses) == 2
        matrix_contexts = [r.matrix_context for r in session.responses]
        assert {"browser": "chrome"} in matrix_contexts
        assert {"browser": "firefox"} in matrix_contexts
