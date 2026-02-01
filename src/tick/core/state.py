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
    """Engine state container with immutable progression tracking.

    Design note: While EngineState itself is immutable (frozen attrs class),
    the contained Session object is intentionally mutable. This is a deliberate
    design choice for performance - avoiding deep copies of the responses list
    on every state transition.

    State transitions (with_response, with_completed) return new EngineState
    instances with updated current_index, while the Session reference is shared
    and mutated in place. This means:
    - EngineState tracks progression through items (current_index is immutable)
    - Session accumulates responses and status changes (mutated in place)

    The engine.save() method persists the current session state to disk.
    """

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

    def with_back(self) -> EngineState:
        """Go back to the previous item, removing the last response.

        Returns a new EngineState with decremented current_index.
        The last response is removed from the session.

        Raises:
            ValueError: If already at the first item (cannot go back).
        """
        if self.current_index == 0:
            raise ValueError("Cannot go back - already at the first item.")
        # Remove the last response
        if self.session.responses:
            self.session.responses.pop()
        return EngineState(
            checklist=self.checklist,
            session=self.session,
            items=self.items,
            current_index=self.current_index - 1,
        )
