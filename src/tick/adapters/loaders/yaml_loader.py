from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from tick.core.models.checklist import Checklist, ChecklistDocument
from tick.core.validator import ValidationIssue, validate_payload


class YamlChecklistLoader:
    def __init__(self) -> None:
        self._yaml = YAML(typ="safe")

    def _read(self, path: Path) -> dict[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            data = self._yaml.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Checklist YAML must be a mapping at the top level.")
        return data

    def _validate_raw(self, raw: dict[str, object]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(validate_payload(raw))
        if issues:
            return issues
        try:
            ChecklistDocument.from_raw(raw)
        except ValidationError as exc:
            for error in exc.errors():
                path_str = ".".join(str(part) for part in error.get("loc", ()))
                issues.append(ValidationIssue(path=path_str, message=error.get("msg", "")))
        return issues

    def validate(self, path: Path) -> list[ValidationIssue]:
        raw = self._read(path)
        return self._validate_raw(raw)

    def load(self, path: Path) -> Checklist:
        raw = self._read(path)
        issues = self._validate_raw(raw)
        if issues:
            formatted = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
            raise ValueError(f"Checklist validation failed: {formatted}")
        document = ChecklistDocument.from_raw(raw)
        return document.checklist
