from __future__ import annotations

from datetime import datetime, timezone

from tick.core.models.checklist import Checklist, ChecklistDocument, compute_checklist_digest
from tick.core.models.enums import ItemResult, SessionStatus
from tick.core.models.session import Response, Session, decode_session, encode_session


def test_checklist_id_slugifies_name():
    checklist = Checklist(
        name="My Checklist!",
        version="1.0.0",
        domain="web",
        sections=[],
    )
    assert checklist.checklist_id == "my-checklist-1.0.0"


def test_checklist_document_from_raw(minimal_checklist_data):
    document = ChecklistDocument.from_raw(minimal_checklist_data)
    assert document.checklist.name == "Minimal Checklist"


def test_session_encode_decode_roundtrip():
    response = Response(
        item_id="item-1",
        result=ItemResult.PASS,
        answered_at=datetime.now(timezone.utc),
        notes="ok",
        evidence=("log.txt",),
    )
    session = Session(
        id="session-123",
        checklist_id="checklist-1.0.0",
        checklist_path="checklist.yaml",
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={"environment": "dev"},
        responses=[response],
    )
    data = encode_session(session)
    decoded = decode_session(data)
    assert decoded.id == session.id
    assert decoded.responses[0].item_id == response.item_id


def test_compute_checklist_digest_is_stable(minimal_checklist):
    first = compute_checklist_digest(minimal_checklist)
    second = compute_checklist_digest(minimal_checklist)
    assert first == second
