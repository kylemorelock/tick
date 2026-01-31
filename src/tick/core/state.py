from __future__ import annotations

from datetime import UTC, datetime

import attrs

from tick.core.models.checklist import Checklist, ChecklistItem
from tick.core.models.enums import SessionStatus
from tick.core.models.session import Response, Session


@attrs.frozen(slots=True)
class ResolvedItem:
    section_name: str
    item: ChecklistItem
    matrix_context: dict[str, str] | None = None

    @property
    def display_check(self) -> str:
        if not self.matrix_context:
            return self.item.check
        details = ", ".join(f"{key}={value}" for key, value in self.matrix_context.items())
        return f"{self.item.check} ({details})"


@attrs.frozen(slots=True)
class EngineState:
    """Immutable engine state - transitions create new instances."""

    checklist: Checklist
    session: Session
    items: tuple[ResolvedItem, ...]
    current_index: int = 0

    @property
    def current_item(self) -> ResolvedItem | None:
        if self.current_index >= len(self.items):
            return None
        return self.items[self.current_index]

    def with_response(self, response: Response) -> EngineState:
        self.session.responses.append(response)
        return EngineState(
            checklist=self.checklist,
            session=self.session,
            items=self.items,
            current_index=self.current_index + 1,
        )

    def with_completed(self) -> EngineState:
        now = datetime.now(UTC)
        self.session.completed_at = now
        self.session.status = SessionStatus.COMPLETED
        return EngineState(
            checklist=self.checklist,
            session=self.session,
            items=self.items,
            current_index=self.current_index,
        )
