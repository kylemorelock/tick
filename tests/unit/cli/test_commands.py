from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from tick.adapters.storage.session_store import SessionStore
from tick.cli.app import app
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session


def _session_id(seed: int) -> str:
    return f"{seed:032x}"


def _write_minimal_checklist(path: Path) -> None:
    path.write_text(
        """
checklist:
  name: "Minimal Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
""".strip(),
        encoding="utf-8",
    )


def _write_matrix_checklist(path: Path) -> None:
    path.write_text(
        """
checklist:
  name: "Matrix Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Matrix"
      items:
        - id: "item-1"
          check: "Matrix check"
          matrix:
            - role: "user"
            - role: "admin"
""".strip(),
        encoding="utf-8",
    )


def test_validate_command_success(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", str(checklist_path)])
    assert result.exit_code == 0


def test_validate_command_failure(tmp_path: Path):
    checklist_path = tmp_path / "bad.yaml"
    checklist_path.write_text("name: bad", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["validate", str(checklist_path)])
    assert result.exit_code == 1


def test_templates_command_lists(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["templates"])
    assert result.exit_code == 0
    assert "web" in result.stdout


def test_init_command_writes_file(tmp_path: Path):
    output_path = tmp_path / "template.yaml"
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--template", "web", "--output", str(output_path)])
    assert result.exit_code == 0
    assert output_path.exists()
    assert "checklist:" in output_path.read_text(encoding="utf-8")


def test_init_command_outputs_to_stdout():
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--template", "web"])
    assert result.exit_code == 0
    assert "checklist:" in result.stdout


def test_init_command_invalid_template(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--template", "unknown"])
    assert result.exit_code == 1


def test_report_command_generates_output(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    session = Session(
        id=_session_id(1),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[
            Response(
                item_id="item-1",
                result=ItemResult.PASS,
                answered_at=datetime.now(UTC),
            )
        ],
        variables={},
    )
    store = SessionStore(tmp_path)
    session_path = store.save(session)

    output_path = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "report",
            str(session_path),
            "--format",
            "json",
            "--checklist",
            str(checklist_path),
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()


def test_report_command_missing_checklist(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    session = Session(
        id=_session_id(2),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[],
        variables={},
    )
    store = SessionStore(tmp_path)
    session_path = store.save(session)
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(session_path)])
    assert result.exit_code == 1


def test_report_command_uses_session_checklist_path(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    session = Session(
        id=_session_id(4),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[],
        variables={},
    )
    store = SessionStore(tmp_path)
    session_path = store.save(session)
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(session_path), "--format", "md"])
    assert result.exit_code == 0
    assert session_path.with_suffix(".md").exists()


def test_report_command_invalid_session_file(tmp_path: Path):
    session_path = tmp_path / "session-bad.json"
    session_path.write_text("not-json", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(session_path), "--format", "json"])
    assert result.exit_code == 1


def test_report_command_digest_mismatch(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    session = Session(
        id=_session_id(5),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[],
        variables={},
    )
    session.checklist_digest = "mismatch"
    store = SessionStore(tmp_path)
    session_path = store.save(session)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "report",
            str(session_path),
            "--format",
            "json",
            "--checklist",
            str(checklist_path),
        ],
    )
    assert result.exit_code == 1


def test_report_command_unsupported_format(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    session = Session(
        id=_session_id(3),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        responses=[],
        variables={},
    )
    store = SessionStore(tmp_path)
    session_path = store.save(session)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "report",
            str(session_path),
            "--format",
            "xml",
            "--checklist",
            str(checklist_path),
        ],
    )
    assert result.exit_code == 1


def test_run_command_non_interactive(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_matrix_checklist(checklist_path)
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
variables:
  environment: "dev"
responses:
  - item_id: "item-1"
    matrix:
      role: "user"
    result: "pass"
    notes: "ok"
    evidence: "log.txt"
  - item_id: "item-1"
    matrix:
      role: "admin"
    result: "fail"
    notes: "needs work"
    evidence:
      - "screenshot.png"
""".strip(),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"
    runner = CliRunner()
    result = runner.invoke(
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
    assert result.exit_code == 0
    assert list(output_dir.glob("session-*.json"))


def test_run_command_resume_missing(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(checklist_path),
            "--output-dir",
            str(output_dir),
            "--resume",
        ],
    )
    assert result.exit_code == 1


def test_run_command_verbose_flag(tmp_path: Path):
    """Verify --verbose flag is accepted and command completes successfully."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  item-1:
    result: pass
""".strip(),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(checklist_path),
            "--output-dir",
            str(output_dir),
            "--no-interactive",
            "--answers",
            str(answers_path),
            "--verbose",
        ],
    )
    assert result.exit_code == 0
    # Verify session was created
    session_files = list(output_dir.glob("session-*.json"))
    assert any(f.name != "session-index.json" for f in session_files)


def test_run_command_dry_run(tmp_path: Path):
    """Verify --dry-run previews items without creating a session."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(checklist_path),
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    # Should show checklist info and items
    assert "Minimal Checklist" in result.stdout
    assert "Would run" in result.stdout
    assert "Do the thing" in result.stdout
    # Should NOT create a session
    assert not output_dir.exists() or not list(output_dir.glob("session-*.json"))


def test_run_command_dry_run_with_resume_fails(tmp_path: Path):
    """Verify --dry-run cannot be combined with --resume."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(checklist_path),
            "--output-dir",
            str(output_dir),
            "--dry-run",
            "--resume",
        ],
    )
    assert result.exit_code == 1
    assert "cannot be combined" in result.stdout.lower()
