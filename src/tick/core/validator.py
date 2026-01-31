from __future__ import annotations

from dataclasses import dataclass

import fastjsonschema  # type: ignore[import-untyped]
from fastjsonschema import JsonSchemaException


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


CHECKLIST_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["checklist"],
    "additionalProperties": False,
    "properties": {
        "checklist": {
            "type": "object",
            "required": ["name", "version", "domain", "sections"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "domain": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "author": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "estimated_time": {"type": "string"},
                    },
                },
                "variables": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["prompt"],
                        "additionalProperties": False,
                        "properties": {
                            "prompt": {"type": "string"},
                            "required": {"type": "boolean"},
                            "options": {"type": "array", "items": {"type": "string"}},
                            "default": {"type": "string"},
                        },
                    },
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "items"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "condition": {"type": "string"},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["id", "check"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "id": {"type": "string"},
                                        "check": {"type": "string"},
                                        "severity": {"type": "string"},
                                        "guidance": {"type": "string"},
                                        "evidence_required": {"type": "boolean"},
                                        "condition": {"type": "string"},
                                        "matrix": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "additionalProperties": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}

_validator = fastjsonschema.compile(CHECKLIST_SCHEMA)


def validate_payload(payload: dict[str, object]) -> list[ValidationIssue]:
    try:
        _validator(payload)
    except JsonSchemaException as exc:
        path = ".".join(str(part) for part in exc.path) if exc.path else ""
        return [ValidationIssue(path=path, message=exc.message)]
    return []
