from __future__ import annotations

from datetime import UTC, datetime

from tick.core.models.checklist import ChecklistItem
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session
from tick.core.state import EngineState, ResolvedItem


def _make_session() -> Session:
    return Session(
        id="session-1",
        checklist_id="checklist-1.0.0",
        checklist_path=None,
        started_at=datetime.now(UTC),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[],
    )


def test_resolved_item_display_with_matrix():
    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item, matrix_context={"role": "admin"})
    assert resolved.display_check == "Check login (role=admin)"


def test_engine_state_current_item_none_when_complete():
    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item)
    state = EngineState(checklist=None, session=_make_session(), items=(resolved,), current_index=1)
    assert state.current_item is None


def test_engine_state_with_response_advances():
    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item)
    state = EngineState(checklist=None, session=_make_session(), items=(resolved,))
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    updated = state.with_response(response)
    assert len(updated.session.responses) == 1
    assert updated.current_index == 1


def test_engine_state_with_completed_sets_status():
    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item)
    state = EngineState(checklist=None, session=_make_session(), items=(resolved,))
    completed = state.with_completed()
    assert completed.session.status == SessionStatus.COMPLETED
    assert completed.session.completed_at is not None


def test_engine_state_session_mutation_is_intentional():
    """Verify that Session is intentionally mutable within frozen EngineState.

    This test documents the design choice: EngineState is immutable (frozen)
    but Session is mutable. State transitions return new EngineState instances
    with updated current_index, while sharing the same Session reference.

    This avoids expensive deep copies of the responses list on each transition.
    """
    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item)
    session = _make_session()
    state = EngineState(checklist=None, session=session, items=(resolved,))

    # Add a response via with_response
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    updated = state.with_response(response)

    # Verify current_index changed (EngineState is new)
    assert state.current_index == 0
    assert updated.current_index == 1

    # Verify Session is shared (intentional mutation)
    assert state.session is updated.session
    assert len(state.session.responses) == 1  # Original state sees the mutation
    assert len(updated.session.responses) == 1

    # This is the intentional design - Session accumulates responses in place
    # while EngineState tracks progression through items


def test_engine_state_with_back_decrements_index():
    """Verify with_back returns to previous item and removes last response."""
    item1 = ChecklistItem(id="item-1", check="First check")
    item2 = ChecklistItem(id="item-2", check="Second check")
    resolved1 = ResolvedItem(section_name="Auth", item=item1)
    resolved2 = ResolvedItem(section_name="Auth", item=item2)
    session = _make_session()
    state = EngineState(checklist=None, session=session, items=(resolved1, resolved2))

    # Record first response
    response1 = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(UTC),
    )
    state = state.with_response(response1)
    assert state.current_index == 1
    assert len(state.session.responses) == 1

    # Record second response
    response2 = Response(
        item_id="item-2",
        result=ItemResult.FAIL,
        answered_at=datetime.now(UTC),
    )
    state = state.with_response(response2)
    assert state.current_index == 2
    assert len(state.session.responses) == 2

    # Go back
    state = state.with_back()
    assert state.current_index == 1
    assert len(state.session.responses) == 1
    assert state.session.responses[0].item_id == "item-1"


def test_engine_state_with_back_raises_at_first_item():
    """Verify with_back raises an error when at the first item."""
    import pytest

    item = ChecklistItem(id="item-1", check="Check login")
    resolved = ResolvedItem(section_name="Auth", item=item)
    session = _make_session()
    state = EngineState(checklist=None, session=session, items=(resolved,))

    with pytest.raises(ValueError, match="Cannot go back"):
        state.with_back()
