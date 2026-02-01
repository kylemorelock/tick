from __future__ import annotations

from tick.core.engine import _expand_items
from tick.core.models.checklist import Checklist, ChecklistItem
from tick.core.models.session import Response, Session
from tick.core.utils import matrix_key


def build_items_by_id(checklist: Checklist) -> dict[str, ChecklistItem]:
    return {item.id: item for section in checklist.sections for item in section.items}


def build_ordered_responses(checklist: Checklist, session: Session) -> list[Response]:
    response_map: dict[tuple[str, tuple[tuple[str, str], ...] | None], Response] = {}
    for response in session.responses:
        response_map[(response.item_id, matrix_key(response.matrix_context))] = response

    if session.resolved_items:
        ordered: list[Response] = []
        used_keys: set[tuple[str, tuple[tuple[str, str], ...] | None]] = set()
        for entry in session.resolved_items:
            if not isinstance(entry, dict):
                continue
            item_id = str(entry.get("item_id", ""))
            matrix_context = entry.get("matrix_context")
            key = (item_id, matrix_key(matrix_context))
            response = response_map.get(key)
            if response:
                ordered.append(response)
                used_keys.add(key)
        if ordered:
            for response in session.responses:
                key = (response.item_id, matrix_key(response.matrix_context))
                if key not in used_keys:
                    ordered.append(response)
            return ordered

    try:
        resolved = _expand_items(checklist, session.variables)
    except ValueError:
        resolved = ()

    if resolved:
        ordered = []
        used_keys = set()
        for item in resolved:
            key = (item.item.id, matrix_key(item.matrix_context))
            response = response_map.get(key)
            if response:
                ordered.append(response)
                used_keys.add(key)
        if ordered:
            for response in session.responses:
                key = (response.item_id, matrix_key(response.matrix_context))
                if key not in used_keys:
                    ordered.append(response)
            return ordered

    return list(session.responses)
