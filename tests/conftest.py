from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ruamel.yaml import YAML

from tick.core.models.checklist import ChecklistDocument
from tick.core.models.enums import SessionStatus
from tick.core.models.session import Session


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically add markers based on test location.

    - tests/unit/ -> @pytest.mark.unit
    - tests/integration/ -> @pytest.mark.integration
    - tests/e2e/ -> @pytest.mark.e2e
    """
    for item in items:
        path = str(item.fspath)
        # Skip if already has the marker (manually specified)
        existing_markers = {m.name for m in item.iter_markers()}

        if "/unit/" in path and "unit" not in existing_markers:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in path and "integration" not in existing_markers:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in path and "e2e" not in existing_markers:
            item.add_marker(pytest.mark.e2e)


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
def large_checklist_path(tmp_path):
    def build_large_checklist(sections: int = 20, items_per_section: int = 25) -> dict[str, object]:
        checklist_sections = []
        for section_index in range(sections):
            items = []
            for item_index in range(items_per_section):
                items.append(
                    {
                        "id": f"sec-{section_index:02d}-item-{item_index:03d}",
                        "check": f"Check {section_index}-{item_index}",
                        "severity": "medium",
                    }
                )
            checklist_sections.append(
                {
                    "name": f"Section {section_index}",
                    "items": items,
                }
            )
        return {
            "checklist": {
                "name": "Large Checklist",
                "version": "1.0.0",
                "domain": "web",
                "sections": checklist_sections,
            }
        }

    data = build_large_checklist()
    path = tmp_path / "large-checklist.yaml"
    yaml = YAML()
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle)
    return path


@pytest.fixture
def in_progress_session(minimal_checklist) -> Session:
    return Session(
        id="session-1",
        checklist_id=minimal_checklist.checklist_id,
        checklist_path=None,
        started_at=datetime.now(UTC),
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
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        status=SessionStatus.COMPLETED,
        variables={"environment": "dev"},
        responses=[],
    )
