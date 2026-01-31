from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from tick.core.models.checklist import Checklist
from tick.core.models.session import Session, SessionSummary
from tick.core.validator import ValidationIssue


@runtime_checkable
class ChecklistLoader(Protocol):
    """Protocol for loading checklists from various sources."""

    def load(self, path: Path) -> Checklist: ...

    def validate(self, path: Path) -> list[ValidationIssue]: ...


@runtime_checkable
class SessionStorage(Protocol):
    """Protocol for persisting session state."""

    def save(self, session: Session) -> Path: ...

    def load(self, session_id: str) -> Session | None: ...

    def list_sessions(self, checklist_id: str) -> list[SessionSummary]: ...


@runtime_checkable
class Reporter(Protocol):
    """Protocol for generating reports from completed sessions."""

    def generate(self, session: Session, checklist: Checklist) -> bytes: ...

    @property
    def content_type(self) -> str: ...

    @property
    def file_extension(self) -> str: ...
