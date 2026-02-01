"""Integration tests for engine + state management.

Tests the ExecutionEngine state transitions and item expansion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.adapters.storage.session_store import SessionStore
from tick.core.engine import ExecutionEngine, _expand_items
from tick.core.models.enums import ItemResult


@pytest.mark.integration
class TestEngineStateTransitions:
    """Test ExecutionEngine state management."""

    def test_engine_start_creates_valid_state(self, tmp_path: Path) -> None:
        """Test that starting an engine creates valid initial state."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "State Test"
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

        loader = YamlChecklistLoader()
        storage = SessionStore(tmp_path / "reports")
        checklist = loader.load(checklist_path)

        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))

        state = engine.state
        assert state.current_index == 0
        assert len(state.items) == 2
        assert state.session.status.value == "in_progress"
        assert engine.current_item is not None
        assert engine.current_item.item.id == "item-1"

    def test_engine_record_response_advances_state(self, tmp_path: Path) -> None:
        """Test that recording responses advances the state."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Progress Test"
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

        loader = YamlChecklistLoader()
        storage = SessionStore(tmp_path / "reports")
        checklist = loader.load(checklist_path)

        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))

        # Record first response
        current = engine.current_item
        assert current is not None
        engine.record_response(
            item=current.item,
            result=ItemResult.PASS,
            notes="Done",
            evidence=["log.txt"],
            matrix_context=None,
        )

        assert engine.state.current_index == 1
        assert len(engine.state.session.responses) == 1
        assert engine.current_item.item.id == "item-2"

        # Record second response
        current = engine.current_item
        engine.record_response(
            item=current.item,
            result=ItemResult.FAIL,
            notes="Issue found",
            evidence=None,
            matrix_context=None,
        )

        assert engine.state.current_index == 2
        assert engine.current_item is None  # No more items

    def test_engine_go_back_removes_response(self, tmp_path: Path) -> None:
        """Test that go_back removes the last response."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Back Test"
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

        loader = YamlChecklistLoader()
        storage = SessionStore(tmp_path / "reports")
        checklist = loader.load(checklist_path)

        engine = ExecutionEngine(loader=loader, storage=storage)
        engine.start(checklist, {}, str(checklist_path))

        # Answer first item
        current = engine.current_item
        engine.record_response(
            item=current.item,
            result=ItemResult.PASS,
            notes="First answer",
            evidence=None,
            matrix_context=None,
        )

        assert engine.state.current_index == 1
        assert len(engine.state.session.responses) == 1

        # Go back
        engine.go_back()

        assert engine.state.current_index == 0
        assert len(engine.state.session.responses) == 0
        assert engine.current_item.item.id == "item-1"

    def test_engine_complete_marks_session_completed(self, tmp_path: Path) -> None:
        """Test that complete() marks session as completed."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Complete Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Only item"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        storage = SessionStore(tmp_path / "reports")
        checklist = loader.load(checklist_path)

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

        engine.complete()

        assert engine.state.session.status.value == "completed"
        assert engine.state.session.completed_at is not None


@pytest.mark.integration
class TestEngineConditionExpansion:
    """Test condition evaluation and item expansion."""

    def test_expand_items_respects_section_condition(self, tmp_path: Path) -> None:
        """Test that section conditions filter items."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Condition Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      required: true
  sections:
    - name: "Always"
      items:
        - id: "always-1"
          check: "Always included"
    - name: "Dev Only"
      condition: "env == 'dev'"
      items:
        - id: "dev-1"
          check: "Dev only"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        # With env=dev, should have 2 items
        items_dev = _expand_items(checklist, {"env": "dev"})
        assert len(items_dev) == 2
        item_ids_dev = [item.item.id for item in items_dev]
        assert "always-1" in item_ids_dev
        assert "dev-1" in item_ids_dev

        # With env=prod, should have 1 item
        items_prod = _expand_items(checklist, {"env": "prod"})
        assert len(items_prod) == 1
        assert items_prod[0].item.id == "always-1"

    def test_expand_items_respects_item_condition(self, tmp_path: Path) -> None:
        """Test that item conditions filter individual items."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Item Condition Test"
  version: "1.0.0"
  domain: "test"
  variables:
    feature:
      prompt: "Feature enabled?"
      required: true
  sections:
    - name: "Features"
      items:
        - id: "base"
          check: "Base check"
        - id: "feature-check"
          check: "Feature-specific"
          condition: "feature == 'on'"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        # With feature=on
        items_on = _expand_items(checklist, {"feature": "on"})
        assert len(items_on) == 2

        # With feature=off
        items_off = _expand_items(checklist, {"feature": "off"})
        assert len(items_off) == 1
        assert items_off[0].item.id == "base"


@pytest.mark.integration
class TestEngineMatrixExpansion:
    """Test matrix item expansion."""

    def test_expand_items_expands_matrix(self, tmp_path: Path) -> None:
        """Test that matrix items are expanded correctly."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Matrix Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Browser Tests"
      items:
        - id: "browser-test"
          check: "Test browser"
          matrix:
            - browser: "chrome"
            - browser: "firefox"
            - browser: "safari"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        items = _expand_items(checklist, {})

        assert len(items) == 3
        browsers = [item.matrix_context["browser"] for item in items]
        assert "chrome" in browsers
        assert "firefox" in browsers
        assert "safari" in browsers

        # All have same item id
        assert all(item.item.id == "browser-test" for item in items)

    def test_matrix_items_have_correct_display_check(self, tmp_path: Path) -> None:
        """Test that matrix items show context in display_check."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Matrix Display Test"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Tests"
      items:
        - id: "test-item"
          check: "Verify functionality"
          matrix:
            - role: "admin"
            - role: "user"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        items = _expand_items(checklist, {})

        # Each should have matrix context reflected in display
        for item in items:
            assert item.matrix_context is not None
            assert "role" in item.matrix_context
            # display_check should include the matrix context
            assert item.matrix_context["role"] in item.display_check
