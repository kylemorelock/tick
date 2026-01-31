from __future__ import annotations

from tick.core.models.checklist import Checklist, ChecklistItem


def build_items_by_id(checklist: Checklist) -> dict[str, ChecklistItem]:
    return {item.id: item for section in checklist.sections for item in section.items}
