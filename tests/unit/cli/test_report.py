from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer

from tick.cli.commands import report as report_module
from tick.cli.commands.report import report_command
from tick.core.models.checklist import ChecklistDocument, compute_checklist_digest
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session, encode_session


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
""".strip()
    )


def _session_id(seed: int) -> str:
    return f"{seed:032x}"


def test_report_command_blocks_overwrite(
    tmp_path: Path, minimal_checklist_data: dict[str, object]
) -> None:
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
    checklist = ChecklistDocument.from_raw(minimal_checklist_data).checklist
    digest = compute_checklist_digest(checklist)
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
        notes=None,
        evidence=(),
        matrix_context=None,
    )
    session = Session(
        id="a" * 32,
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=digest,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[response],
    )
    session_path = tmp_path / "session-a.json"
    session_path.write_bytes(encode_session(session))

    output_path = tmp_path / "report.html"
    output_path.write_text("existing")
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=output_path,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_rejects_non_json_session(tmp_path: Path) -> None:
    session_path = tmp_path / "session.txt"
    session_path.write_text("not-json")
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=None,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_rejects_session_path_directory(tmp_path: Path) -> None:
    session_path = tmp_path / "session-bad.json"
    session_path.mkdir()
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=None,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_rejects_bad_checklist_extension(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.txt"
    checklist_path.write_text("bad")
    session = Session(
        id=_session_id(1),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_rejects_checklist_traversal(tmp_path: Path) -> None:
    session = Session(
        id=_session_id(8),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=None,
        checklist_digest=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=Path("../checklist.yaml"),
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_resolves_relative_checklist_path(monkeypatch, tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    session = Session(
        id=_session_id(11),
        checklist_id=checklist.checklist_id,
        checklist_path=None,
        checklist_digest=compute_checklist_digest(checklist),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    output_path = tmp_path / "report.html"

    monkeypatch.chdir(tmp_path)
    report_command(
        session_path=session_path,
        format="html",
        checklist_path=Path("checklist.yaml"),
        output_path=output_path,
        overwrite=False,
    )
    assert output_path.exists()


def test_report_command_load_session_failure(monkeypatch, tmp_path: Path) -> None:
    session_path = tmp_path / "session-bad.json"
    session_path.write_text("bad", encoding="utf-8")

    def boom(self, _path):
        raise OSError("boom")

    monkeypatch.setattr(report_module.SessionStore, "load_from_path", boom)
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=None,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_load_checklist_failure(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    checklist_path.write_text("checklist: bad", encoding="utf-8")
    session = Session(
        id=_session_id(9),
        checklist_id="minimal-checklist-1.0.0",
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_updates_missing_digest(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    session = Session(
        id=_session_id(2),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[response],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    output_path = tmp_path / "report.html"

    report_command(
        session_path=session_path,
        format="html",
        checklist_path=checklist_path,
        output_path=output_path,
        overwrite=False,
    )
    assert output_path.exists()
    from tick.core.models.session import decode_session

    updated_session = decode_session(session_path.read_bytes())
    assert updated_session.checklist_digest == compute_checklist_digest(checklist)


def test_report_command_update_digest_write_failure(monkeypatch, tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    session = Session(
        id=_session_id(6),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))

    original_atomic = report_module.atomic_write_bytes

    def boom(path, data):
        if path == session_path:
            raise OSError("boom")
        return original_atomic(path, data)

    monkeypatch.setattr(report_module, "atomic_write_bytes", boom)
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=None,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_rejects_missing_output_dir(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    session = Session(
        id=_session_id(3),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=compute_checklist_digest(checklist),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    output_path = tmp_path / "missing" / "report.html"

    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=output_path,
            overwrite=False,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_overwrites_existing_output(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    session = Session(
        id=_session_id(7),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=compute_checklist_digest(checklist),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[response],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    output_path = tmp_path / "report.html"
    output_path.write_text("old", encoding="utf-8")

    report_command(
        session_path=session_path,
        format="html",
        checklist_path=checklist_path,
        output_path=output_path,
        overwrite=True,
    )
    assert "old" not in output_path.read_text(encoding="utf-8")


def test_report_command_rejects_output_path_directory(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    session = Session(
        id=_session_id(10),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=compute_checklist_digest(checklist),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))
    output_path = tmp_path / "output-dir"
    output_path.mkdir()
    with pytest.raises(typer.Exit) as excinfo:
        report_command(
            session_path=session_path,
            format="html",
            checklist_path=checklist_path,
            output_path=output_path,
            overwrite=True,
        )
    assert excinfo.value.exit_code == 1


def test_report_command_custom_template(tmp_path: Path) -> None:
    """Verify --template flag uses a custom Jinja2 template."""
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    checklist = ChecklistDocument.from_raw(
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
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    session = Session(
        id=_session_id(12),
        checklist_id=checklist.checklist_id,
        checklist_path=str(checklist_path),
        checklist_digest=compute_checklist_digest(checklist),
        started_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={},
        responses=[response],
    )
    session_path = tmp_path / f"session-{session.id}.json"
    session_path.write_bytes(encode_session(session))

    # Create a custom template
    template_path = tmp_path / "custom-template.j2"
    template_path.write_text(
        """<!DOCTYPE html>
<html>
<head><title>CUSTOM: {{ checklist.name }}</title></head>
<body>
<h1>CUSTOM REPORT</h1>
<p>Total items: {{ stats.total }}</p>
{% for row in rows %}
<div>{{ row.id }}: {{ row.result }}</div>
{% endfor %}
</body>
</html>""",
        encoding="utf-8",
    )

    output_path = tmp_path / "report.html"
    report_command(
        session_path=session_path,
        format="html",
        checklist_path=checklist_path,
        output_path=output_path,
        overwrite=False,
        template_path=template_path,
    )
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "CUSTOM REPORT" in content
    assert "CUSTOM: Minimal Checklist" in content
    assert "Total items: 1" in content
