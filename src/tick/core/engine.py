from __future__ import annotations

import ast
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from tick.core.models.checklist import Checklist, ChecklistItem
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session
from tick.core.protocols import ChecklistLoader, SessionStorage
from tick.core.state import EngineState, ResolvedItem
from tick.core.utils import ensure_session_digest, matrix_key, validate_session_digest


def _safe_eval_condition(condition: str, variables: dict[str, object]) -> bool:
    if not condition:
        return True

    allowed_nodes = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Name,
        ast.Constant,
        ast.Load,
        ast.List,
        ast.Tuple,
        ast.And,
        ast.Or,
        ast.Eq,
        ast.NotEq,
        ast.In,
        ast.NotIn,
        ast.Not,
    )

    def _eval(node: ast.AST) -> object:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BoolOp):
            values = [_eval(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
            raise ValueError("Unsupported boolean operator")  # pragma: no cover - defensive
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not _eval(node.operand)
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                right = _eval(comparator)
                if isinstance(op, ast.Eq) and not (left == right):
                    return False
                if isinstance(op, ast.NotEq) and not (left != right):
                    return False
                if isinstance(op, ast.In) and not (left in right):
                    return False
                if isinstance(op, ast.NotIn) and not (left not in right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id not in variables or variables[node.id] is None:
                raise ValueError("Missing variable")
            return variables[node.id]
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            return [_eval(element) for element in node.elts]
        raise ValueError("Unsupported expression")  # pragma: no cover - defensive

    try:
        parsed = ast.parse(condition, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid condition: {condition}") from exc
    if any(not isinstance(node, allowed_nodes) for node in ast.walk(parsed)):
        raise ValueError(f"Unsupported expression in condition: {condition}")
    return bool(_eval(parsed))


def _expand_items(
    checklist: Checklist, variables: dict[str, object]
) -> tuple[ResolvedItem, ...]:
    resolved: list[ResolvedItem] = []
    for section in checklist.sections:
        if section.condition and not _safe_eval_condition(section.condition, variables):
            continue
        for item in section.items:
            if item.condition and not _safe_eval_condition(item.condition, variables):
                continue
            if item.matrix:
                for entry in item.matrix:
                    resolved.append(
                        ResolvedItem(
                            section_name=section.name,
                            item=item,
                            matrix_context=entry,
                        )
                    )
            else:
                resolved.append(ResolvedItem(section_name=section.name, item=item))
    return tuple(resolved)


class ExecutionEngine:
    """Drives checklist execution with explicit state transitions."""

    def __init__(self, loader: ChecklistLoader, storage: SessionStorage):
        self._loader = loader
        self._storage = storage
        self._state: EngineState | None = None

    @property
    def state(self) -> EngineState:
        if self._state is None:
            raise RuntimeError("Engine has not been started.")
        return self._state

    @property
    def current_item(self) -> ResolvedItem | None:
        return self.state.current_item

    def start(self, checklist: Checklist, variables: dict[str, object], checklist_path: str) -> None:
        normalized = dict(variables)
        session = Session(
            id=uuid4().hex,
            checklist_id=checklist.checklist_id,
            checklist_path=checklist_path,
            started_at=datetime.now(timezone.utc),
            status=SessionStatus.IN_PROGRESS,
            variables=normalized,
            responses=[],
        )
        ensure_session_digest(session, checklist)
        items = _expand_items(checklist, normalized)
        self._state = EngineState(checklist=checklist, session=session, items=items)

    def resume(self, checklist: Checklist, session: Session) -> None:
        validate_session_digest(session, checklist)
        items = _expand_items(checklist, session.variables)
        if len(session.responses) > len(items):
            raise ValueError("Session responses do not match the checklist items.")
        for index, response in enumerate(session.responses):
            item = items[index]
            if response.item_id != item.item.id:
                raise ValueError("Session responses do not match the checklist items.")
            if matrix_key(response.matrix_context) != matrix_key(item.matrix_context):
                raise ValueError("Session responses do not match the checklist items.")
        current_index = len(session.responses)
        self._state = EngineState(
            checklist=checklist,
            session=session,
            items=items,
            current_index=current_index,
        )

    def record_response(
        self,
        item: ChecklistItem,
        result: ItemResult,
        notes: str | None,
        evidence: Iterable[str] | None,
        matrix_context: dict[str, str] | None,
    ) -> None:
        response = Response(
            item_id=item.id,
            result=result,
            answered_at=datetime.now(timezone.utc),
            notes=notes,
            evidence=tuple(evidence or ()),
            matrix_context=matrix_context,
        )
        self._state = self.state.with_response(response)

    def complete(self) -> None:
        self._state = self.state.with_completed()

    def save(self) -> None:
        self._storage.save(self.state.session)
