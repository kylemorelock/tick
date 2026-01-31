from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tick.core.models.checklist import ChecklistDocument
from tick.core.models.enums import SessionStatus
from tick.core.models.session import Session


@pytest.fixture
def minimal_checklist_data() -> dict[str, object]:
    return {
        "checklist": {
            "name": "Minimal Checklist",
            "version": "1.0.0",
            "domain": "web",
            "sections": [
                {
                    "name": "Basics",
                    "items": [
                        {"id": "item-1", "check": "Do the thing"},
                    ],
                }
            ],
        }
    }


@pytest.fixture
def minimal_checklist(minimal_checklist_data):
    return ChecklistDocument.from_raw(minimal_checklist_data).checklist


@pytest.fixture
def complex_checklist_data() -> dict[str, object]:
    return {
        "checklist": {
            "name": "Complex Checklist",
            "version": "2.0.0",
            "domain": "api",
            "metadata": {
                "author": "QA Team",
                "tags": ["smoke"],
                "estimated_time": "30 minutes",
            },
            "variables": {
                "environment": {
                    "prompt": "Environment",
                    "required": True,
                    "options": ["dev", "prod"],
                },
                "feature_flag": {
                    "prompt": "Feature flag",
                    "default": "on",
                },
            },
            "sections": [
                {
                    "name": "Conditional Section",
                    "condition": "environment != 'prod'",
                    "items": [
                        {
                            "id": "cond-1",
                            "check": "Conditional check",
                            "severity": "low",
                            "guidance": "Run only outside prod.",
                            "evidence_required": True,
                        },
                        {
                            "id": "matrix-1",
                            "check": "Matrix check",
                            "matrix": [
                                {"role": "user"},
                                {"role": "admin"},
                            ],
                        },
                    ],
                },
                {
                    "name": "Always Section",
                    "items": [
                        {
                            "id": "always-1",
                            "check": "Always check",
                            "condition": "feature_flag == 'on'",
                        }
                    ],
                },
            ],
        }
    }


@pytest.fixture
def complex_checklist(complex_checklist_data):
    return ChecklistDocument.from_raw(complex_checklist_data).checklist


@pytest.fixture
def in_progress_session(minimal_checklist) -> Session:
    return Session(
        id="session-1",
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.IN_PROGRESS,
        variables={},
        responses=[],
    )


@pytest.fixture
def completed_session(minimal_checklist) -> Session:
    return Session(
        id="session-2",
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status=SessionStatus.COMPLETED,
        variables={"environment": "dev"},
        responses=[],
    )
