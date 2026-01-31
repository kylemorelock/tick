from __future__ import annotations

from datetime import datetime, timezone

from tick.core.models.checklist import ChecklistItem
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session
from tick.core.state import EngineState, ResolvedItem


def _make_session() -> Session:
    return Session(
        id="session-1",
        checklist_id="checklist-1.0.0",
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
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
        answered_at=datetime.now(timezone.utc),
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
