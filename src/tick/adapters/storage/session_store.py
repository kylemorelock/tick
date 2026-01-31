from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import msgspec
from msgspec import DecodeError

from tick.core.models.enums import SessionStatus
from tick.core.models.session import Session, SessionSummary, decode_session, encode_session
from tick.core.utils import atomic_write_bytes


class SessionIndexEntry(msgspec.Struct):
    id: str
    checklist_id: str
    status: SessionStatus
    started_at: datetime
    updated_at: float


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._index_encoder = msgspec.json.Encoder()
        self._index_decoder = msgspec.json.Decoder(list[SessionIndexEntry])

    def _validate_session_id(self, session_id: str) -> str:
        if not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise ValueError("Invalid session id.")
        return session_id

    def _path_for(self, session_id: str) -> Path:
        safe_id = self._validate_session_id(session_id)
        return self._base_dir / f"session-{safe_id}.json"

    def _index_path(self) -> Path:
        return self._base_dir / "session-index.json"

    def _load_index(self) -> dict[str, SessionIndexEntry] | None:
        path = self._index_path()
        if not path.exists():
            return None
        try:
            entries = self._index_decoder.decode(path.read_bytes())
        except (OSError, DecodeError, ValueError, TypeError):
            return None
        return {entry.id: entry for entry in entries}

    def _save_index(self, entries: Iterable[SessionIndexEntry]) -> None:
        payload = self._index_encoder.encode(list(entries))
        atomic_write_bytes(self._index_path(), payload)

    def _scan_sessions(self) -> dict[str, SessionIndexEntry]:
        entries: dict[str, SessionIndexEntry] = {}
        for path in self._base_dir.glob("session-*.json"):
            try:
                session = decode_session(path.read_bytes())
            except (OSError, DecodeError, ValueError, TypeError):
                continue
            entries[session.id] = SessionIndexEntry(
                id=session.id,
                checklist_id=session.checklist_id,
                status=session.status,
                started_at=session.started_at,
                updated_at=path.stat().st_mtime,
            )
        return entries

    def save(self, session: Session) -> Path:
        path = self._path_for(session.id)
        payload = encode_session(session)
        atomic_write_bytes(path, payload)
        entries = self._load_index() or self._scan_sessions()
        entries[session.id] = SessionIndexEntry(
            id=session.id,
            checklist_id=session.checklist_id,
            status=session.status,
            started_at=session.started_at,
            updated_at=time.time(),
        )
        try:
            self._save_index(entries.values())
        except OSError:
            pass
        return path

    def load(self, session_id: str) -> Session | None:
        try:
            path = self._path_for(session_id)
        except ValueError:
            return None
        if not path.exists():
            return None
        try:
            return decode_session(path.read_bytes())
        except (OSError, DecodeError, ValueError, TypeError):
            return None

    def load_from_path(self, path: Path) -> Session:
        if not path.is_file():
            raise ValueError("Session path must be a file.")
        if not path.name.startswith("session-") or path.suffix.lower() != ".json":
            raise ValueError("Session file name must be session-<id>.json.")
        return decode_session(path.read_bytes())

    def list_sessions(self, checklist_id: str) -> list[SessionSummary]:
        entries = self._load_index()
        if entries is None:
            entries = self._scan_sessions()
            try:
                self._save_index(entries.values())
            except OSError:
                pass
        summaries = [
            SessionSummary(
                id=entry.id,
                checklist_id=entry.checklist_id,
                started_at=entry.started_at,
                status=entry.status,
            )
            for entry in entries.values()
            if entry.checklist_id == checklist_id
        ]
        return summaries

    def find_latest_in_progress(self, checklist_id: str) -> Session | None:
        entries = self._load_index()
        if entries is None:
            entries = self._scan_sessions()
            try:
                self._save_index(entries.values())
            except OSError:
                pass
        candidates = [
            entry
            for entry in entries.values()
            if entry.checklist_id == checklist_id and entry.status == SessionStatus.IN_PROGRESS
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda entry: entry.updated_at, reverse=True)
        return self.load(candidates[0].id)
