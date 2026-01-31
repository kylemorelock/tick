from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from tick.core.models.enums import Severity


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "checklist"


class ChecklistVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    required: bool = False
    options: list[str] | None = None
    default: str | None = None


class ChecklistMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    estimated_time: str | None = None


class ChecklistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    check: str
    severity: Severity = Severity.MEDIUM
    guidance: str | None = None
    evidence_required: bool = False
    condition: str | None = None
    matrix: list[dict[str, str]] | None = None


class ChecklistSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    condition: str | None = None
    items: list[ChecklistItem] = Field(default_factory=list)


class Checklist(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    domain: str
    metadata: ChecklistMetadata = Field(default_factory=ChecklistMetadata)
    variables: dict[str, ChecklistVariable] = Field(default_factory=dict)
    sections: list[ChecklistSection] = Field(default_factory=list)
    _digest_cache: str | None = PrivateAttr(default=None)

    @property
    def checklist_id(self) -> str:
        return f"{_slugify(self.name)}-{self.version}"


def compute_checklist_digest(checklist: Checklist) -> str:
    if getattr(checklist, "_digest_cache", None):
        return checklist._digest_cache  # type: ignore[return-value]
    payload = checklist.model_dump(mode="json")
    normalized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    checklist._digest_cache = digest
    return digest


class ChecklistDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checklist: Checklist

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "ChecklistDocument":
        return cls.model_validate(raw)
