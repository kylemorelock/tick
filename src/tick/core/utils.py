from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from tick.core.models.checklist import Checklist, compute_checklist_digest
from tick.core.models.session import Session
from tick.core.state import ResolvedItem


def matrix_key(matrix: Mapping[str, object] | None) -> tuple[tuple[str, str], ...] | None:
    if matrix is None or not isinstance(matrix, dict):
        return None
    return tuple(sorted((str(key), str(value)) for key, value in matrix.items()))


def normalize_evidence(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, (list, tuple)):
        return [str(entry) for entry in raw if str(entry).strip()]
    return []


def build_resolved_items_payload(items: Iterable[ResolvedItem]) -> list[dict[str, object]]:
    return [
        {
            "section_name": resolved.section_name,
            "item_id": resolved.item.id,
            "check": resolved.item.check,
            "severity": resolved.item.severity.value,
            "guidance": resolved.item.guidance,
            "evidence_required": resolved.item.evidence_required,
            "matrix_context": resolved.matrix_context,
        }
        for resolved in items
    ]


def validate_session_digest(session: Session, checklist: Checklist) -> str:
    digest = compute_checklist_digest(checklist)
    if session.checklist_digest and session.checklist_digest != digest:
        raise ValueError("Checklist contents do not match the saved session.")
    return digest


def ensure_session_digest(session: Session, checklist: Checklist) -> bool:
    digest = compute_checklist_digest(checklist)
    if session.checklist_digest is None:
        session.checklist_digest = digest
        return True
    return False


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        Path(temp_path).replace(path)
    finally:
        if os.path.exists(temp_path):
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
