from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import time

import msgspec

from tick.core.models.checklist import Checklist, ChecklistItem, compute_checklist_digest
from tick.core.state import ResolvedItem
from tick.core.validator import ValidationIssue

CACHE_VERSION = 1


@dataclass(frozen=True)
class FileFingerprint:
    path: str
    size: int
    mtime: float
    sha256: str

    @property
    def signature(self) -> str:
        payload = f"{self.path}|{self.size}|{self.mtime}|{self.sha256}".encode()
        return hashlib.sha256(payload).hexdigest()


class CacheIssue(msgspec.Struct, frozen=True):
    path: str
    message: str


class ChecklistCacheEntry(msgspec.Struct, frozen=True):
    cache_version: int
    raw: dict[str, object] | None
    issues: list[CacheIssue]
    created_at: float


class ExpansionItem(msgspec.Struct, frozen=True):
    section_name: str
    item_id: str
    matrix_context: dict[str, str] | None


class ExpansionCacheEntry(msgspec.Struct, frozen=True):
    cache_version: int
    items: list[ExpansionItem]
    created_at: float


class CacheStats(msgspec.Struct, frozen=True):
    checklist_entries: int
    expansion_entries: int
    total_bytes: int


def fingerprint_path(path: Path, data: bytes) -> FileFingerprint:
    stat = path.stat()
    digest = hashlib.sha256(data).hexdigest()
    return FileFingerprint(
        path=str(path.resolve()),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=digest,
    )


def _default_cache_dir() -> Path:
    env_override = os.environ.get("TICK_CACHE_DIR")
    if env_override:
        return Path(env_override)
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "tick"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "tick"
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "tick" / "Cache"
    return Path.home() / ".cache" / "tick"


def _variables_digest(variables: Mapping[str, object]) -> str:
    normalized = {key: str(value) for key, value in variables.items()}
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_item_index(checklist: Checklist) -> dict[str, tuple[ChecklistItem, str]]:
    mapping: dict[str, tuple[ChecklistItem, str]] = {}
    for section in checklist.sections:
        for item in section.items:
            mapping[item.id] = (item, section.name)
    return mapping


class ChecklistCache:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or _default_cache_dir()
        self._checklists_dir = self._cache_dir / "checklists"
        self._expansions_dir = self._cache_dir / "expansions"
        self._checklists_dir.mkdir(parents=True, exist_ok=True)
        self._expansions_dir.mkdir(parents=True, exist_ok=True)
        self._checklist_encoder = msgspec.json.Encoder()
        self._checklist_decoder = msgspec.json.Decoder(ChecklistCacheEntry)
        self._expansion_encoder = msgspec.json.Encoder()
        self._expansion_decoder = msgspec.json.Decoder(ExpansionCacheEntry)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def read_checklist_entry(self, fingerprint: FileFingerprint) -> ChecklistCacheEntry | None:
        path = self._checklists_dir / f"{fingerprint.signature}.json"
        if not path.exists():
            return None
        try:
            entry = self._checklist_decoder.decode(path.read_bytes())
        except (msgspec.DecodeError, OSError):
            return None
        if entry.cache_version != CACHE_VERSION:
            return None
        return entry

    def write_checklist_entry(
        self,
        fingerprint: FileFingerprint,
        raw: dict[str, object] | None,
        issues: list[ValidationIssue],
    ) -> None:
        path = self._checklists_dir / f"{fingerprint.signature}.json"
        issue_entries = [CacheIssue(path=issue.path, message=issue.message) for issue in issues]
        entry = ChecklistCacheEntry(
            cache_version=CACHE_VERSION,
            raw=raw,
            issues=issue_entries,
            created_at=time(),
        )
        try:
            path.write_bytes(self._checklist_encoder.encode(entry))
        except OSError:
            return

    def read_expansion(
        self, checklist: Checklist, variables: Mapping[str, object]
    ) -> tuple[ResolvedItem, ...] | None:
        checklist_digest = compute_checklist_digest(checklist)
        variables_digest = _variables_digest(variables)
        signature = hashlib.sha256(
            f"{checklist_digest}|{variables_digest}".encode()
        ).hexdigest()
        path = self._expansions_dir / f"{signature}.json"
        if not path.exists():
            return None
        try:
            entry = self._expansion_decoder.decode(path.read_bytes())
        except (msgspec.DecodeError, OSError):
            return None
        if entry.cache_version != CACHE_VERSION:
            return None
        item_index = _build_item_index(checklist)
        resolved: list[ResolvedItem] = []
        for cached in entry.items:
            item_data = item_index.get(cached.item_id)
            if not item_data:
                return None
            item, _section_name = item_data
            resolved.append(
                ResolvedItem(
                    section_name=cached.section_name,
                    item=item,
                    matrix_context=cached.matrix_context,
                )
            )
        return tuple(resolved)

    def write_expansion(
        self, checklist: Checklist, variables: Mapping[str, object], items: tuple[ResolvedItem, ...]
    ) -> None:
        checklist_digest = compute_checklist_digest(checklist)
        variables_digest = _variables_digest(variables)
        signature = hashlib.sha256(
            f"{checklist_digest}|{variables_digest}".encode()
        ).hexdigest()
        path = self._expansions_dir / f"{signature}.json"
        entry = ExpansionCacheEntry(
            cache_version=CACHE_VERSION,
            items=[
                ExpansionItem(
                    section_name=item.section_name,
                    item_id=item.item.id,
                    matrix_context=item.matrix_context,
                )
                for item in items
            ],
            created_at=time(),
        )
        try:
            path.write_bytes(self._expansion_encoder.encode(entry))
        except OSError:
            return

    def stats(self) -> CacheStats:
        checklist_entries = list(self._checklists_dir.glob("*.json"))
        expansion_entries = list(self._expansions_dir.glob("*.json"))
        total_bytes = sum(path.stat().st_size for path in checklist_entries + expansion_entries)
        return CacheStats(
            checklist_entries=len(checklist_entries),
            expansion_entries=len(expansion_entries),
            total_bytes=total_bytes,
        )

    def clean(self) -> None:
        for path in self._checklists_dir.glob("*.json"):
            path.unlink(missing_ok=True)
        for path in self._expansions_dir.glob("*.json"):
            path.unlink(missing_ok=True)

    def prune(self, max_age_days: int) -> None:
        cutoff = time() - (max_age_days * 86400)
        for path in list(self._checklists_dir.glob("*.json")) + list(
            self._expansions_dir.glob("*.json")
        ):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
