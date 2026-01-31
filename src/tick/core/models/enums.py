from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ItemResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    NOT_APPLICABLE = "na"


class SessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
