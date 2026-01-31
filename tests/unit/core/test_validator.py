from __future__ import annotations

from tick.core.validator import validate_payload


def test_validate_payload_accepts_minimal(minimal_checklist_data):
    issues = validate_payload(minimal_checklist_data)
    assert issues == []


def test_validate_payload_rejects_missing_root():
    issues = validate_payload({"name": "bad"})
    assert issues


def test_validate_payload_rejects_extra_fields(minimal_checklist_data):
    payload = dict(minimal_checklist_data)
    payload["extra"] = "nope"
    issues = validate_payload(payload)
    assert issues
