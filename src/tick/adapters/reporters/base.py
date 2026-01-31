from __future__ import annotations

from abc import ABC, abstractmethod

from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


class ReporterBase(ABC):
    @property
    @abstractmethod
    def content_type(self) -> str: ...

    @property
    @abstractmethod
    def file_extension(self) -> str: ...

    @abstractmethod
    def generate(self, session: Session, checklist: Checklist) -> bytes: ...
