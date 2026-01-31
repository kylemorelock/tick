from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import os
import pytest
import typer

from tick.cli.commands.run import run_command
from tick.core.models.checklist import ChecklistDocument, compute_checklist_digest
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session, decode_session, encode_session


def _session_file(output_dir: Path) -> Path:
    return next(
        path
        for path in output_dir.glob("session-*.json")
        if path.name != "session-index.json"
    )


def test_run_command_requires_variables(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
        """
checklist:
  name: "Minimal Checklist"
  version: "1.0.0"
  domain: "web"
  variables:
    env:
      prompt: "Environment"
      required: true
      options: ["prod"]
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
""".strip()
    )
    output_dir = tmp_path / "reports"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=None,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_parses_evidence(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  item-1:
    result: pass
    evidence: "link-1, link-2"
""".strip()
    )
    output_dir = tmp_path / "reports"
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=True,
        answers=answers_path,
        resume=False,
    )
    session_path = _session_file(output_dir)
    session = decode_session(session_path.read_bytes())
    assert session.responses[0].evidence == ("link-1", "link-2")


def test_run_command_resume_digest_mismatch(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    session = Session(
        id="c" * 32,
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest="deadbeef",
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[],
    )
    session_path = output_dir / "session-c.json"
    session_path.write_bytes(encode_session(session))
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=False,
            answers=None,
            resume=True,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_invalid_answers_yaml(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text("responses: [", encoding="utf-8")
    output_dir = tmp_path / "reports"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=answers_path,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_missing_answers_file(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    missing_answers = tmp_path / "missing.yaml"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=missing_answers,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_invalid_checklist(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text("name: bad", encoding="utf-8")
    output_dir = tmp_path / "reports"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=None,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_invalid_variables_mapping(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
        """
checklist:
  name: "Minimal Checklist"
  version: "1.0.0"
  domain: "web"
  variables:
    env:
      prompt: "Environment"
      required: true
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text("variables: [1, 2]", encoding="utf-8")
    output_dir = tmp_path / "reports"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=answers_path,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_output_dir_not_writable(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    os.chmod(output_dir, 0o500)
    try:
        with pytest.raises(typer.Exit) as excinfo:
            run_command(
                checklist=checklist_path,
                output_dir=output_dir,
                no_interactive=True,
                answers=None,
                resume=False,
            )
        assert excinfo.value.exit_code == 1
    finally:
        os.chmod(output_dir, 0o700)


def test_run_command_output_dir_is_file(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.write_text("not-a-dir", encoding="utf-8")
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=None,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_warns_on_unused_answers(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  item-1:
    result: pass
  extra-1:
    result: fail
""".strip(),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=True,
        answers=answers_path,
        resume=False,
    )
    assert list(output_dir.glob("session-*.json"))


def test_run_command_resume_sets_digest(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(timezone.utc),
    )
    session = Session(
        id="d" * 32,
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[response],
    )
    session_path = output_dir / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))

    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=True,
    )
    updated = decode_session(session_path.read_bytes())
    assert updated.checklist_digest is not None


def test_run_command_resume_with_existing_digest(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(timezone.utc),
    )
    session = Session(
        id="f" * 32,
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest=compute_checklist_digest(
            ChecklistDocument.from_raw(
                {
                    "checklist": {
                        "name": "Minimal Checklist",
                        "version": "1.0.0",
                        "domain": "web",
                        "sections": [
                            {"name": "Basics", "items": [{"id": "item-1", "check": "Do the thing"}]}
                        ],
                    }
                }
            ).checklist
        ),
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[response],
    )
    session_path = output_dir / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))

    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=True,
    )
    updated = decode_session(session_path.read_bytes())
    assert updated.checklist_digest == session.checklist_digest


def test_run_command_resume_rejects_mismatched_session(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    response = Response(
        item_id="wrong",
        result=ItemResult.PASS,
        answered_at=datetime.now(timezone.utc),
    )
    session = Session(
        id="e" * 32,
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[response],
    )
    session_path = output_dir / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))

    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=False,
            answers=None,
            resume=True,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_non_interactive_uses_answer(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  item-1:
    result: fail
    notes: "failed"
""".strip()
    )
    output_dir = tmp_path / "reports"
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=True,
        answers=answers_path,
        resume=False,
    )
    session_path = _session_file(output_dir)
    session = decode_session(session_path.read_bytes())
    assert session.responses[0].result == ItemResult.FAIL


def test_run_command_non_interactive_matrix_no_match(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text(
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
""".strip()
    )
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  - item_id: "item-1"
    matrix:
      role: "guest"
    result: pass
""".strip()
    )
    output_dir = tmp_path / "reports"
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=True,
        answers=answers_path,
        resume=False,
    )
    session_path = _session_file(output_dir)
    session = decode_session(session_path.read_bytes())
    assert len(session.responses) == 2
