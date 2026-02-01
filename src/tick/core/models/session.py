from __future__ import annotations

from datetime import datetime

import msgspec

from tick.core.models.enums import ItemResult, SessionStatus


class Response(msgspec.Struct, frozen=True, array_like=True):
    """Immutable response record - optimized for fast serialization."""

    item_id: str
    result: ItemResult
    answered_at: datetime
    notes: str | None = None
    evidence: tuple[str, ...] = ()
    matrix_context: dict[str, str] | None = None


class Session(msgspec.Struct):
    """Session state - mutable during execution, fast JSON persistence.

    Note: Session is intentionally mutable (not frozen) because responses
    accumulate during execution. This avoids expensive deep copies when
    adding responses. The EngineState class wraps Session and provides
    immutable progression tracking via current_index.

    Responses are appended in place, and status/completed_at are updated
    when the session completes. Use encode_session/decode_session for
    serialization.
    """

    id: str
    checklist_id: str
    started_at: datetime
    checklist_path: str | None = None
    checklist_digest: str | None = None
    completed_at: datetime | None = None
    status: SessionStatus = SessionStatus.IN_PROGRESS
    variables: dict[str, str] = msgspec.field(default_factory=dict)
    responses: list[Response] = msgspec.field(default_factory=list)


class SessionSummary(msgspec.Struct, frozen=True):
    id: str
    checklist_id: str
    started_at: datetime
    status: SessionStatus


_encoder = msgspec.json.Encoder()
_decoder = msgspec.json.Decoder(Session)


def encode_session(session: Session) -> bytes:
    return _encoder.encode(session)


def decode_session(data: bytes) -> Session:
    return _decoder.decode(data)
