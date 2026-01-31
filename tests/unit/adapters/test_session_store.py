from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import msgspec

from tick.adapters.storage.session_store import SessionStore
from tick.adapters.storage import session_store as session_store_module
from tick.core.models.enums import SessionStatus
from tick.core.models.session import Session


def _session_id(seed: int) -> str:
    return f"{seed:032x}"


def _make_session(session_id: str, checklist_id: str, status: SessionStatus) -> Session:
    return Session(
        id=session_id,
        checklist_id=checklist_id,
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        status=status,
        variables={},
        responses=[],
    )


def test_session_store_save_load(tmp_path: Path):
    store = SessionStore(tmp_path)
    session = _make_session(_session_id(1), "check-1", SessionStatus.IN_PROGRESS)
    saved_path = store.save(session)
    assert saved_path.exists()
    loaded = store.load(_session_id(1))
    assert loaded is not None
    assert loaded.id == _session_id(1)


def test_session_store_load_missing_returns_none(tmp_path: Path):
    store = SessionStore(tmp_path)
    assert store.load(_session_id(2)) is None


def test_session_store_load_invalid_id_returns_none(tmp_path: Path):
    store = SessionStore(tmp_path)
    assert store.load("bad-id") is None


def test_session_store_load_corrupt_returns_none(tmp_path: Path):
    store = SessionStore(tmp_path)
    corrupt_path = tmp_path / "session-bad.json"
    corrupt_path.write_text("not-json", encoding="utf-8")
    assert store.load(_session_id(3)) is None


def test_session_store_load_decode_error_returns_none(monkeypatch, tmp_path: Path):
    store = SessionStore(tmp_path)
    session = _make_session(_session_id(10), "check-1", SessionStatus.IN_PROGRESS)
    store.save(session)

    def boom(_data):
        raise msgspec.DecodeError("bad")

    monkeypatch.setattr(session_store_module, "decode_session", boom)
    assert store.load(session.id) is None


def test_session_store_list_sessions_filters_by_checklist(tmp_path: Path):
    store = SessionStore(tmp_path)
    (tmp_path / "session-corrupt.json").write_text("bad", encoding="utf-8")
    store.save(_make_session(_session_id(4), "check-1", SessionStatus.IN_PROGRESS))
    store.save(_make_session(_session_id(5), "check-2", SessionStatus.IN_PROGRESS))
    results = store.list_sessions("check-1")
    assert len(results) == 1
    assert results[0].id == _session_id(4)


def test_session_store_find_latest_in_progress(tmp_path: Path):
    store = SessionStore(tmp_path)
    (tmp_path / "session-corrupt.json").write_text("bad", encoding="utf-8")
    session_old = _make_session(_session_id(6), "check-1", SessionStatus.IN_PROGRESS)
    session_new = _make_session(_session_id(7), "check-1", SessionStatus.IN_PROGRESS)
    store.save(session_old)
    time.sleep(0.01)
    store.save(session_new)
    latest = store.find_latest_in_progress("check-1")
    assert latest is not None
    assert latest.id == _session_id(7)


def test_session_store_find_latest_skips_completed(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save(_make_session(_session_id(11), "check-1", SessionStatus.COMPLETED))
    in_progress = _make_session(_session_id(12), "check-1", SessionStatus.IN_PROGRESS)
    store.save(in_progress)
    latest = store.find_latest_in_progress("check-1")
    assert latest is not None
    assert latest.id == _session_id(12)


def test_session_store_find_latest_skips_other_checklist(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save(_make_session(_session_id(13), "check-2", SessionStatus.IN_PROGRESS))
    assert store.find_latest_in_progress("check-1") is None


def test_session_store_find_latest_in_progress_none_when_completed(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save(_make_session(_session_id(8), "check-1", SessionStatus.COMPLETED))
    assert store.find_latest_in_progress("check-1") is None


def test_session_store_load_from_path(tmp_path: Path):
    store = SessionStore(tmp_path)
    session = _make_session(_session_id(9), "check-1", SessionStatus.IN_PROGRESS)
    path = store.save(session)
    loaded = store.load_from_path(path)
    assert loaded.id == session.id
