import os

from ruamel.yaml import YAML

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.core.cache import ChecklistCache
from tick.core.engine import _expand_items


def _write_yaml(path, data: dict[str, object]) -> None:
    yaml = YAML()
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle)


def test_checklist_cache_roundtrip(tmp_path, minimal_checklist_data):
    checklist_path = tmp_path / "checklist.yaml"
    _write_yaml(checklist_path, minimal_checklist_data)
    cache = ChecklistCache(tmp_path / "cache")
    loader = YamlChecklistLoader(cache=cache)

    loader.load(checklist_path)
    stats = cache.stats()
    assert stats.checklist_entries == 1

    loader.load(checklist_path)
    stats_after = cache.stats()
    assert stats_after.checklist_entries == 1


def test_checklist_cache_invalidation(tmp_path, minimal_checklist_data):
    checklist_path = tmp_path / "checklist.yaml"
    _write_yaml(checklist_path, minimal_checklist_data)
    cache = ChecklistCache(tmp_path / "cache")
    loader = YamlChecklistLoader(cache=cache)

    loader.load(checklist_path)
    stats = cache.stats()
    assert stats.checklist_entries == 1

    modified = {**minimal_checklist_data}
    modified["checklist"] = {**modified["checklist"], "version": "1.0.1"}
    _write_yaml(checklist_path, modified)
    loader.load(checklist_path)
    stats_after = cache.stats()
    assert stats_after.checklist_entries == 2


def test_expansion_cache_roundtrip(minimal_checklist, tmp_path):
    cache = ChecklistCache(tmp_path / "cache")
    variables: dict[str, object] = {}
    items = _expand_items(minimal_checklist, variables)

    cache.write_expansion(minimal_checklist, variables, items)
    cached = cache.read_expansion(minimal_checklist, variables)

    assert cached is not None
    assert len(cached) == len(items)
    assert [item.item.id for item in cached] == [item.item.id for item in items]


def test_cache_prune_removes_old_entries(tmp_path, minimal_checklist_data):
    checklist_path = tmp_path / "checklist.yaml"
    _write_yaml(checklist_path, minimal_checklist_data)
    cache = ChecklistCache(tmp_path / "cache")
    loader = YamlChecklistLoader(cache=cache)
    loader.load(checklist_path)

    entries = list((tmp_path / "cache" / "checklists").glob("*.json"))
    assert entries
    old_mtime = 1
    for entry in entries:
        os.utime(entry, (old_mtime, old_mtime))

    cache.prune(max_age_days=1)
    stats = cache.stats()
    assert stats.checklist_entries == 0
