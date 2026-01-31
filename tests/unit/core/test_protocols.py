from __future__ import annotations

from pathlib import Path

from tick.core.models.checklist import Checklist
from tick.core.models.session import Session
from tick.core.protocols import ChecklistLoader, Reporter, SessionStorage


class DummyLoader:
    def load(self, path: Path) -> Checklist:
        raise NotImplementedError

    def validate(self, path: Path):
        return []


class DummyStorage:
    def save(self, session: Session):
        return Path("session.json")

    def load(self, session_id: str):
        return None

    def list_sessions(self, checklist_id: str):
        return []


class DummyReporter:
    content_type = "text/plain"
    file_extension = "txt"

    def generate(self, session: Session, checklist: Checklist):
        return b"ok"


def test_protocol_runtime_checks():
    assert isinstance(DummyLoader(), ChecklistLoader)
    assert isinstance(DummyStorage(), SessionStorage)
    assert isinstance(DummyReporter(), Reporter)
