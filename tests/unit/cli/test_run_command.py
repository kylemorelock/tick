from __future__ import annotations

from pathlib import Path

import pytest
import typer

from tick.cli.commands import run as run_module
from tick.cli.commands.run import (
    _load_answers,
    _normalize_responses,
    _parse_result,
    _resolve_variables,
    run_command,
)
from tick.core.models.checklist import ChecklistVariable
from tick.core.models.enums import ItemResult
from tick.core.state import ResolvedItem
from tick.core.utils import matrix_key, normalize_evidence


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


def _write_variable_checklist(path: Path) -> None:
    path.write_text(
        """
checklist:
  name: "Variables Checklist"
  version: "1.0.0"
  domain: "web"
  variables:
    environment:
      prompt: "Environment"
      required: true
      options: ["dev", "prod"]
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
""".strip(),
        encoding="utf-8",
    )


def test_load_answers_returns_empty_for_non_mapping(tmp_path: Path):
    path = tmp_path / "answers.yaml"
    path.write_text("- item", encoding="utf-8")
    with pytest.raises(ValueError, match=r"mapping"):
        _load_answers(path)


def test_load_answers_empty_file_returns_empty(tmp_path: Path):
    path = tmp_path / "answers.yaml"
    path.write_text("", encoding="utf-8")
    assert _load_answers(path) == {}


def test_normalize_responses_accepts_dict_and_list():
    data = {"responses": {"item-1": {"result": "pass"}}}
    normalized = _normalize_responses(data)
    assert normalized["item-1"][0]["result"] == "pass"

    data_none = {"responses": {"item-2": None}}
    normalized_none = _normalize_responses(data_none)
    assert normalized_none["item-2"][0]["item_id"] == "item-2"

    data_list = {"responses": [{"item_id": "item-2", "result": "fail"}]}
    normalized_list = _normalize_responses(data_list)
    assert normalized_list["item-2"][0]["result"] == "fail"

    data_other = {"responses": "nope"}
    assert _normalize_responses(data_other) == {}
    data_bad_dict = {"responses": {"item-1": "bad"}}
    assert _normalize_responses(data_bad_dict) == {}
    data_missing_id = {"responses": [{"result": "pass"}]}
    assert _normalize_responses(data_missing_id) == {}


def test_parse_result_defaults():
    assert _parse_result(None) == ItemResult.SKIP
    assert _parse_result("unknown") == ItemResult.SKIP
    assert _parse_result("PASS") == ItemResult.PASS
    assert _parse_result("p") == ItemResult.PASS
    assert _parse_result("s") == ItemResult.SKIP
    assert _parse_result("n") == ItemResult.NOT_APPLICABLE
    assert _parse_result("na") == ItemResult.NOT_APPLICABLE


def test_matrix_key_normalization():
    assert matrix_key(None) is None
    assert matrix_key({"b": 2, "a": 1}) == (("a", "1"), ("b", "2"))
    assert matrix_key("nope") is None


def test_normalize_evidence_variants():
    assert normalize_evidence("a, b") == ["a", "b"]
    assert normalize_evidence(["a", 2, " "]) == ["a", "2"]
    assert normalize_evidence(5) == []


def test_resolve_variables_defaults_and_options():
    variables = {"environment": "dev", "feature": ""}
    specs = {
        "environment": ChecklistVariable(
            prompt="Environment", required=True, options=["dev", "prod"]
        ),
        "feature": ChecklistVariable(prompt="Feature", default="on"),
    }
    resolved, errors = _resolve_variables(variables, specs)
    assert errors == []
    assert resolved["environment"] == "dev"
    assert resolved["feature"] == "on"


def test_resolve_variables_reports_errors():
    variables = {"environment": "staging"}
    specs = {
        "environment": ChecklistVariable(
            prompt="Environment", required=True, options=["dev", "prod"]
        ),
        "required": ChecklistVariable(prompt="Required", required=True),
    }
    _, errors = _resolve_variables(variables, specs)
    assert len(errors) == 2


def test_resolve_variables_skips_none_optional():
    variables = {}
    specs = {"optional": ChecklistVariable(prompt="Optional")}
    resolved, errors = _resolve_variables(variables, specs)
    assert errors == []
    assert "optional" not in resolved


def test_run_command_interactive(monkeypatch, tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"

    monkeypatch.setattr(run_module, "ask_variables", lambda variables, console: {"env": "dev"})

    def fake_item_response(*args, **kwargs):
        return ItemResult.PASS, "ok", ["log.txt"]

    monkeypatch.setattr(run_module, "ask_item_response", fake_item_response)
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=False,
    )
    assert list(output_dir.glob("session-*.json"))


def test_run_command_resume_with_answers(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text(
        """
responses:
  item-1:
    result: "pass"
    evidence: "log.txt"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=answers_path,
            resume=True,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_no_interactive_missing_variables(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_variable_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text("variables: {}", encoding="utf-8")
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=answers_path,
            resume=False,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_resume_digest_mismatch(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=True,
            answers=None,
            resume=True,
        )
    assert excinfo.value.exit_code == 1


def test_run_command_no_interactive_skips_missing_answers(tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"
    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=True,
        answers=None,
        resume=False,
    )
    session_files = list(output_dir.glob("session-*.json"))
    assert session_files


def test_run_command_breaks_on_none_current_item(monkeypatch, tmp_path: Path):
    checklist_path = tmp_path / "checklist.yaml"
    _write_minimal_checklist(checklist_path)
    output_dir = tmp_path / "reports"

    sequence = [ResolvedItem(section_name="Basics", item=None), None]

    def fake_current_item(self):
        return sequence.pop(0)

    monkeypatch.setattr(run_module, "ask_variables", lambda variables, console: {})
    monkeypatch.setattr(
        run_module, "ask_item_response", lambda *args, **kwargs: (ItemResult.PASS, None, [])
    )
    monkeypatch.setattr(run_module.ExecutionEngine, "current_item", property(fake_current_item))

    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=False,
    )
    assert list(output_dir.glob("session-*.json"))


def _write_multi_item_checklist(path: Path) -> None:
    path.write_text(
        """
checklist:
  name: "Multi Item Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "First item"
        - id: "item-2"
          check: "Second item"
        - id: "item-3"
          check: "Third item"
""".strip(),
        encoding="utf-8",
    )


def test_run_command_autosave_after_each_response(monkeypatch, tmp_path: Path):
    """Verify that sessions are auto-saved after each response in interactive mode."""
    from tick.core.models.session import decode_session

    checklist_path = tmp_path / "checklist.yaml"
    _write_multi_item_checklist(checklist_path)
    output_dir = tmp_path / "reports"

    response_count = 0
    saved_response_counts: list[int] = []

    monkeypatch.setattr(run_module, "ask_variables", lambda variables, console: {})

    def fake_item_response(*args, **kwargs):
        nonlocal response_count
        response_count += 1
        return ItemResult.PASS, f"note {response_count}", []

    monkeypatch.setattr(run_module, "ask_item_response", fake_item_response)

    # Track save calls to verify auto-save behavior
    original_save = run_module.SessionStore.save

    def tracking_save(self, session):
        saved_response_counts.append(len(session.responses))
        return original_save(self, session)

    monkeypatch.setattr(run_module.SessionStore, "save", tracking_save)

    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=False,
    )

    # Should have saved: once at start (0 responses), then after each of 3 responses,
    # plus final save at the end
    # Expected: [0, 1, 2, 3, 3] - initial save, after each response, final save
    assert len(saved_response_counts) >= 4  # At least initial + 3 responses
    # Verify incremental saves happened (responses grew from 0 to 3)
    assert 0 in saved_response_counts  # Initial save with 0 responses
    assert 1 in saved_response_counts  # After first response
    assert 2 in saved_response_counts  # After second response
    assert 3 in saved_response_counts  # After third response

    # Verify final session file has all responses
    # Filter out session-index.json which is also created by SessionStore
    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]
    assert len(session_files) == 1
    session = decode_session(session_files[0].read_bytes())
    assert len(session.responses) == 3


def test_run_command_keyboard_interrupt_saves_session(monkeypatch, tmp_path: Path):
    """Verify Ctrl+C gracefully saves session and exits cleanly."""
    from tick.core.models.session import decode_session

    checklist_path = tmp_path / "checklist.yaml"
    _write_multi_item_checklist(checklist_path)
    output_dir = tmp_path / "reports"

    response_count = 0

    monkeypatch.setattr(run_module, "ask_variables", lambda variables, console: {})

    def fake_item_response_with_interrupt(*args, **kwargs):
        nonlocal response_count
        response_count += 1
        if response_count == 2:
            raise KeyboardInterrupt
        return ItemResult.PASS, f"note {response_count}", []

    monkeypatch.setattr(run_module, "ask_item_response", fake_item_response_with_interrupt)

    with pytest.raises(typer.Exit) as excinfo:
        run_command(
            checklist=checklist_path,
            output_dir=output_dir,
            no_interactive=False,
            answers=None,
            resume=False,
        )

    # Should exit with code 0 (graceful exit)
    assert excinfo.value.exit_code == 0

    # Verify session was saved with partial progress
    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]
    assert len(session_files) == 1
    session = decode_session(session_files[0].read_bytes())
    # Should have 1 response (interrupted on 2nd)
    assert len(session.responses) == 1
    # Session should still be in progress (not completed)
    from tick.core.models.enums import SessionStatus

    assert session.status == SessionStatus.IN_PROGRESS


def test_run_command_back_navigation(monkeypatch, tmp_path: Path):
    """Verify back navigation allows user to change previous responses."""
    from tick.core.models.session import decode_session

    checklist_path = tmp_path / "checklist.yaml"
    _write_multi_item_checklist(checklist_path)
    output_dir = tmp_path / "reports"

    call_count = 0

    monkeypatch.setattr(run_module, "ask_variables", lambda variables, console: {})

    def fake_item_response_with_back(item, console, can_go_back=False):
        nonlocal call_count
        call_count += 1
        # Sequence: answer item 1, answer item 2, go back, re-answer item 2, answer item 3
        if call_count == 1:
            return ItemResult.PASS, "first", []
        if call_count == 2:
            return ItemResult.FAIL, "wrong answer", []
        if call_count == 3:
            # Go back to fix the wrong answer
            return None, None, []  # None result means go back
        if call_count == 4:
            return ItemResult.PASS, "corrected", []
        # call_count == 5
        return ItemResult.PASS, "third", []

    monkeypatch.setattr(run_module, "ask_item_response", fake_item_response_with_back)

    run_command(
        checklist=checklist_path,
        output_dir=output_dir,
        no_interactive=False,
        answers=None,
        resume=False,
    )

    # Verify final session
    session_files = [f for f in output_dir.glob("session-*.json") if f.name != "session-index.json"]
    assert len(session_files) == 1
    session = decode_session(session_files[0].read_bytes())
    assert len(session.responses) == 3

    # Verify the second response was corrected
    assert session.responses[1].notes == "corrected"
    assert session.responses[1].result.value == "pass"
