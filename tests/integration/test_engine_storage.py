"""Integration tests for engine + storage.

Tests the ExecutionEngine working with SessionStore for persistence and resume.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.adapters.storage.session_store import SessionStore
from tick.core.engine import ExecutionEngine
from tick.core.models.enums import ItemResult


@pytest.mark.integration
class TestEngineSaveLoad:
    """Test engine save/load with SessionStore."""

    def test_engine_save_creates_session_file(self, tmp_path: Path) -> None:
        """Test that engine.save() creates a session file."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Save Test"
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

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))
        engine.save()

        # Verify session file was created
        session_files = list(output_dir.glob("session-*.json"))
        session_files = [f for f in session_files if "index" not in f.name]
        assert len(session_files) == 1

    def test_session_round_trip(self, tmp_path: Path) -> None:
        """Test that session data survives save/load round trip."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Round Trip Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First"
        - id: "item-2"
          check: "Second"
""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        # Create session and record a response
        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))

        current = engine.current_item
        engine.record_response(
            item=current.item,
            result=ItemResult.PASS,
            notes="Test notes",
            evidence=["file.txt", "screen.png"],
            matrix_context=None,
        )
        engine.save()

        session_id = engine.state.session.id

        # Load session back
        loaded_session = storage.load(session_id)
        assert loaded_session is not None
        assert loaded_session.id == session_id
        assert len(loaded_session.responses) == 1
        assert loaded_session.responses[0].result == ItemResult.PASS
        assert loaded_session.responses[0].notes == "Test notes"
        assert "file.txt" in loaded_session.responses[0].evidence


@pytest.mark.integration
class TestEngineResume:
    """Test engine resume functionality."""

    def test_engine_resume_continues_from_saved_state(self, tmp_path: Path) -> None:
        """Test that engine.resume() continues from saved state."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Resume Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First"
        - id: "item-2"
          check: "Second"
        - id: "item-3"
          check: "Third"
""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        # First engine: start and answer first item
        engine1 = ExecutionEngine(loader=loader, storage=storage)
        engine1.start(checklist, {}, str(checklist_path))

        current = engine1.current_item
        engine1.record_response(
            item=current.item,
            result=ItemResult.PASS,
            notes="First answer",
            evidence=None,
            matrix_context=None,
        )
        engine1.save()

        session = engine1.state.session

        # Second engine: resume from saved session
        engine2 = ExecutionEngine(loader=loader, storage=storage)
        engine2.resume(checklist, session)

        # Should be at item-2
        assert engine2.state.current_index == 1
        assert engine2.current_item.item.id == "item-2"
        assert len(engine2.state.session.responses) == 1

    def test_resume_validates_responses_match_items(self, tmp_path: Path) -> None:
        """Test that resume validates session responses match checklist."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Validation Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "First"
        - id: "item-2"
          check: "Second"
""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        # Start session
        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))

        current = engine.current_item
        engine.record_response(
            item=current.item,
            result=ItemResult.PASS,
            notes=None,
            evidence=None,
            matrix_context=None,
        )
        engine.save()

        # Resume should work with matching checklist
        session = storage.load(engine.state.session.id)
        engine2 = ExecutionEngine(loader=loader, storage=storage)
        engine2.resume(checklist, session)  # Should not raise

    def test_find_latest_in_progress_session(self, tmp_path: Path) -> None:
        """Test finding the latest in-progress session."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Find Latest Test"
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

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        # No sessions initially
        found = storage.find_latest_in_progress(checklist.checklist_id)
        assert found is None

        # Create an in-progress session
        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))
        engine.save()

        # Now should find it
        found = storage.find_latest_in_progress(checklist.checklist_id)
        assert found is not None
        assert found.id == engine.state.session.id


@pytest.mark.integration
class TestEngineWithVariables:
    """Test engine with variable-driven checklists."""

    def test_session_stores_variables(self, tmp_path: Path) -> None:
        """Test that session stores variable values."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      required: true
    region:
      prompt: "Region"
      default: "us-east"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {"env": "prod", "region": "eu-west"}, str(checklist_path))
        engine.save()

        # Load and verify variables
        loaded = storage.load(engine.state.session.id)
        assert loaded.variables["env"] == "prod"
        assert loaded.variables["region"] == "eu-west"

    def test_resume_uses_saved_variables(self, tmp_path: Path) -> None:
        """Test that resume uses the session's saved variables."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Resume Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      required: true
  sections:
    - name: "Dev Only"
      condition: "env == 'dev'"
      items:
        - id: "dev-item"
          check: "Dev check"
    - name: "Always"
      items:
        - id: "always-item"
          check: "Always check"
""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "reports"
        loader = YamlChecklistLoader()
        storage = SessionStore(output_dir)
        checklist = loader.load(checklist_path)

        # Start with env=dev (2 items)
        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {"env": "dev"}, str(checklist_path))
        engine.save()

        assert len(engine.state.items) == 2

        # Resume should use saved env=dev
        session = storage.load(engine.state.session.id)
        engine2 = ExecutionEngine(loader=loader, storage=storage)
        engine2.resume(checklist, session)

        # Should still have 2 items
        assert len(engine2.state.items) == 2
