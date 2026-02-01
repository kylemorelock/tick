from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from tick.core.cache import ChecklistCache, FileFingerprint, fingerprint_path
from tick.core.models.checklist import Checklist, ChecklistDocument
from tick.core.validator import ValidationIssue, validate_payload


class YamlChecklistLoader:
    def __init__(self, cache: ChecklistCache | None = None) -> None:
        self._yaml = YAML(typ="safe")
        self._cache = cache

    def _read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def _parse_bytes(self, data: bytes) -> dict[str, object]:
        text = data.decode("utf-8")
        parsed = self._yaml.load(text)
        if not isinstance(parsed, dict):
            raise ValueError("Checklist YAML must be a mapping at the top level.")
        return parsed

    def _fingerprint(self, path: Path, data: bytes) -> FileFingerprint | None:
        if not self._cache:
            return None
        return fingerprint_path(path, data)

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
        data = self._read_bytes(path)
        fingerprint = self._fingerprint(path, data)
        if self._cache and fingerprint:
            cached = self._cache.read_checklist_entry(fingerprint)
            if cached is not None:
                return [ValidationIssue(path=issue.path, message=issue.message) for issue in cached.issues]
        raw = self._parse_bytes(data)
        issues = self._validate_raw(raw)
        if self._cache and fingerprint:
            self._cache.write_checklist_entry(
                fingerprint=fingerprint,
                raw=raw if not issues else None,
                issues=issues,
            )
        return issues

    def load(self, path: Path) -> Checklist:
        data = self._read_bytes(path)
        fingerprint = self._fingerprint(path, data)
        if self._cache and fingerprint:
            cached = self._cache.read_checklist_entry(fingerprint)
            if cached is not None and cached.raw is not None and not cached.issues:
                document = ChecklistDocument.from_raw(cached.raw)
                return document.checklist
            if cached is not None and cached.issues:
                formatted = "; ".join(
                    f"{issue.path}: {issue.message}" for issue in cached.issues
                )
                raise ValueError(f"Checklist validation failed: {formatted}")
        raw = self._parse_bytes(data)
        issues = self._validate_raw(raw)
        if issues:
            formatted = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
            if self._cache and fingerprint:
                self._cache.write_checklist_entry(fingerprint, None, issues)
            raise ValueError(f"Checklist validation failed: {formatted}")
        document = ChecklistDocument.from_raw(raw)
        if self._cache and fingerprint:
            self._cache.write_checklist_entry(fingerprint, raw, [])
        return document.checklist
