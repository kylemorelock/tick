"""Integration tests for complete tick workflows.

These tests exercise the full CLI workflow from checklist to report.
"""

from __future__ import annotations

from pathlib import Path

import msgspec
import pytest
from typer.testing import CliRunner

from tick.cli.app import app
from tick.core.models.session import decode_session


def _write_test_checklist(path: Path) -> None:
    """Write a checklist with multiple items for testing."""
    path.write_text(
        """
checklist:
  name: "Integration Test Checklist"
  version: "1.0.0"
  domain: "test"
  metadata:
    author: "Test Author"
    tags: ["integration", "test"]
  variables:
    environment:
      prompt: "Environment"
      options: ["dev", "staging", "prod"]
      default: "dev"
  sections:
    - name: "Basic Checks"
      items:
        - id: "basic-001"
          check: "Verify basic functionality"
          severity: "high"
        - id: "basic-002"
          check: "Check error handling"
          severity: "medium"
    - name: "Advanced Checks"
      condition: "environment != 'prod'"
      items:
        - id: "adv-001"
          check: "Test advanced feature"
          severity: "low"
          evidence_required: true
""".strip(),
        encoding="utf-8",
    )


@pytest.mark.integration
def test_full_workflow_non_interactive(tmp_path: Path):
    """Test complete non-interactive workflow: run -> verify session -> generate report."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_test_checklist(checklist_path)

    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
variables:
  environment: "staging"
responses:
  basic-001:
    result: pass
    notes: "All checks passed"
    evidence: "log1.txt, screenshot.png"
  basic-002:
    result: fail
    notes: "Error handling needs improvement"
  adv-001:
    result: skip
    notes: "Skipped for now"
""".strip(),
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"
    runner = CliRunner()

    # Step 1: Run the checklist non-interactively
    run_result = runner.invoke(
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
    assert run_result.exit_code == 0, f"Run failed: {run_result.stdout}"

    # Step 2: Verify session file was created and has correct structure
    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]
    assert len(session_files) == 1

    session = decode_session(session_files[0].read_bytes())
    assert session.checklist_id == "integration-test-checklist-1.0.0"
    assert session.status.value == "completed"
    assert len(session.responses) == 3
    assert session.variables["environment"] == "staging"

    # Verify response details
    response_map = {r.item_id: r for r in session.responses}
    assert response_map["basic-001"].result.value == "pass"
    assert response_map["basic-001"].notes == "All checks passed"
    assert "log1.txt" in response_map["basic-001"].evidence
    assert response_map["basic-002"].result.value == "fail"
    assert response_map["adv-001"].result.value == "skip"

    # Step 3: Generate HTML report
    report_result = runner.invoke(
        app,
        [
            "report",
            str(session_files[0]),
            "--format",
            "html",
            "--checklist",
            str(checklist_path),
        ],
    )
    assert report_result.exit_code == 0, f"Report failed: {report_result.stdout}"

    # Verify HTML report was created
    html_path = session_files[0].with_suffix(".html")
    assert html_path.exists()
    html_content = html_path.read_text(encoding="utf-8")
    assert "Integration Test Checklist" in html_content
    assert "summary-card pass" in html_content  # Stats section
    assert "basic-001" in html_content


@pytest.mark.integration
def test_full_workflow_generate_markdown_report(tmp_path: Path):
    """Test generating a markdown report from a session."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_test_checklist(checklist_path)

    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
variables:
  environment: "dev"
responses:
  basic-001:
    result: pass
  basic-002:
    result: pass
  adv-001:
    result: na
""".strip(),
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"
    runner = CliRunner()

    # Run the checklist
    run_result = runner.invoke(
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
    assert run_result.exit_code == 0

    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]
    assert len(session_files) == 1

    # Generate markdown report
    report_result = runner.invoke(
        app,
        [
            "report",
            str(session_files[0]),
            "--format",
            "md",
            "--checklist",
            str(checklist_path),
        ],
    )
    assert report_result.exit_code == 0

    md_path = session_files[0].with_suffix(".md")
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "# Integration Test Checklist" in md_content
    assert "## Summary" in md_content
    assert "**Pass**: 2" in md_content
    assert "**N/A**: 1" in md_content


@pytest.mark.integration
def test_full_workflow_json_report_includes_stats(tmp_path: Path):
    """Test generating a JSON report with statistics."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_test_checklist(checklist_path)

    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
variables:
  environment: "prod"
responses:
  basic-001:
    result: pass
  basic-002:
    result: fail
""".strip(),
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"
    runner = CliRunner()

    # Run the checklist (with prod, adv-001 should be excluded by condition)
    run_result = runner.invoke(
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
    assert run_result.exit_code == 0

    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]

    # Generate JSON report
    json_output = tmp_path / "report.json"
    report_result = runner.invoke(
        app,
        [
            "report",
            str(session_files[0]),
            "--format",
            "json",
            "--checklist",
            str(checklist_path),
            "--output",
            str(json_output),
        ],
    )
    assert report_result.exit_code == 0

    report_data = msgspec.json.decode(json_output.read_bytes())
    assert "stats" in report_data
    assert report_data["stats"]["pass"] == 1
    assert report_data["stats"]["fail"] == 1
    assert report_data["stats"]["total"] == 2


@pytest.mark.integration
def test_init_validate_run_workflow(tmp_path: Path):
    """Test the workflow from init template to validate to run."""
    runner = CliRunner()

    # Step 1: Initialize from template
    checklist_path = tmp_path / "my-checklist.yaml"
    init_result = runner.invoke(
        app,
        ["init", "--template", "web", "--output", str(checklist_path)],
    )
    assert init_result.exit_code == 0
    assert checklist_path.exists()

    # Step 2: Validate the checklist
    validate_result = runner.invoke(app, ["validate", str(checklist_path)])
    assert validate_result.exit_code == 0

    # Step 3: Dry-run to see items
    dry_run_result = runner.invoke(
        app,
        ["run", str(checklist_path), "--dry-run"],
    )
    assert dry_run_result.exit_code == 0
    assert "Would run" in dry_run_result.stdout


@pytest.mark.integration
def test_dry_run_shows_conditional_items(tmp_path: Path):
    """Test that dry-run correctly shows/hides items based on conditions."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_test_checklist(checklist_path)

    answers_path = tmp_path / "answers.yaml"
    runner = CliRunner()

    # With environment=staging, should see all 3 items (adv-001 included)
    answers_path.write_text("variables:\n  environment: staging", encoding="utf-8")
    result_staging = runner.invoke(
        app,
        ["run", str(checklist_path), "--dry-run", "--answers", str(answers_path)],
    )
    assert result_staging.exit_code == 0
    assert "Would run 3 items" in result_staging.stdout
    assert "adv-001" in result_staging.stdout or "Test advanced feature" in result_staging.stdout

    # With environment=prod, should see only 2 items (adv-001 excluded by condition)
    answers_path.write_text("variables:\n  environment: prod", encoding="utf-8")
    result_prod = runner.invoke(
        app,
        ["run", str(checklist_path), "--dry-run", "--answers", str(answers_path)],
    )
    assert result_prod.exit_code == 0
    assert "Would run 2 items" in result_prod.stdout
