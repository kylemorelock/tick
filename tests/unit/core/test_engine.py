from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tick.core.engine import ExecutionEngine
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session


class DummyLoader:
    def load(self, path):
        raise NotImplementedError

    def validate(self, path):
        return []


class DummyStorage:
    def __init__(self):
        self.saved: Session | None = None

    def save(self, session: Session):
        self.saved = session
        return None

    def load(self, session_id: str):
        return None

    def list_sessions(self, checklist_id: str):
        return []


def test_engine_records_response(minimal_checklist):
    engine = ExecutionEngine(loader=DummyLoader(), storage=DummyStorage())
    engine.start(minimal_checklist, variables={}, checklist_path="checklist.yaml")
    current = engine.current_item
    assert current is not None
    engine.record_response(
        item=current.item,
        result=ItemResult.PASS,
        notes=None,
        evidence=None,
        matrix_context=None,
    )
    engine.complete()
    assert engine.state.session.status == SessionStatus.COMPLETED
    assert len(engine.state.session.responses) == 1


def test_engine_state_before_start_raises():
    engine = ExecutionEngine(loader=DummyLoader(), storage=DummyStorage())
    with pytest.raises(RuntimeError, match=r"not been started"):
        _ = engine.state


def test_engine_resume_advances_index(minimal_checklist, in_progress_session):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    in_progress_session.responses = [
        Response(
            item_id="item-1",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
        )
    ]
    engine.resume(minimal_checklist, in_progress_session)
    assert engine.state.current_index == len(in_progress_session.responses)


def test_engine_resume_digest_mismatch_raises(minimal_checklist, in_progress_session):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    in_progress_session.checklist_digest = "mismatch"
    with pytest.raises(ValueError, match=r"do not match"):
        engine.resume(minimal_checklist, in_progress_session)


def test_engine_resume_rejects_extra_responses(minimal_checklist, in_progress_session):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    in_progress_session.responses = [
        Response(
            item_id="item-1",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
        ),
        Response(
            item_id="item-1",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
        ),
    ]
    with pytest.raises(ValueError, match=r"responses"):
        engine.resume(minimal_checklist, in_progress_session)


def test_engine_resume_rejects_item_mismatch(minimal_checklist, in_progress_session):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    in_progress_session.responses = [
        Response(
            item_id="wrong",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
        )
    ]
    with pytest.raises(ValueError, match=r"responses"):
        engine.resume(minimal_checklist, in_progress_session)


def test_engine_resume_rejects_matrix_mismatch(complex_checklist, in_progress_session):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    in_progress_session.checklist_id = complex_checklist.checklist_id
    in_progress_session.variables = {"environment": "dev", "feature_flag": "on"}
    in_progress_session.responses = [
        Response(
            item_id="cond-1",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
        ),
        Response(
            item_id="matrix-1",
            result=ItemResult.PASS,
            answered_at=datetime.now(UTC),
            matrix_context={"role": "wrong"},
        ),
    ]
    with pytest.raises(ValueError, match=r"responses"):
        engine.resume(complex_checklist, in_progress_session)


def test_engine_save_persists_session(minimal_checklist):
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    engine.start(minimal_checklist, variables={}, checklist_path="checklist.yaml")
    engine.save()
    assert storage.saved is not None


def test_engine_go_back_returns_to_previous_item(minimal_checklist):
    """Verify go_back() returns to previous item and removes response."""
    storage = DummyStorage()
    engine = ExecutionEngine(loader=DummyLoader(), storage=storage)
    engine.start(minimal_checklist, variables={}, checklist_path="checklist.yaml")

    # Record a response
    current = engine.current_item
    engine.record_response(
        item=current.item,
        result=ItemResult.PASS,
        notes="test",
        evidence=None,
        matrix_context=None,
    )
    assert engine.state.current_index == 1
    assert len(engine.state.session.responses) == 1

    # Go back
    engine.go_back()
    assert engine.state.current_index == 0
    assert len(engine.state.session.responses) == 0
    assert engine.current_item is not None
