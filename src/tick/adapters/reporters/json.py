from __future__ import annotations

import msgspec

from tick.adapters.reporters.base import ReporterBase
from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


class JsonReporter(ReporterBase):
    content_type = "application/json"
    file_extension = "json"

    def __init__(self) -> None:
        self._encoder = msgspec.json.Encoder()

    def generate(self, session: Session, checklist: Checklist) -> bytes:
        payload = {
            "checklist": checklist.model_dump(),
            "session": msgspec.to_builtins(session),
        }
        return self._encoder.encode(payload)
