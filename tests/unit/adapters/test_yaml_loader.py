from __future__ import annotations

from pathlib import Path

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader


def test_yaml_loader_loads_minimal(tmp_path: Path):
    path = tmp_path / "checklist.yaml"
    path.write_text(
        """
checklist:
  name: "Minimal Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
""".strip()
    )
    loader = YamlChecklistLoader()
    checklist = loader.load(path)
    assert checklist.name == "Minimal Checklist"


def test_yaml_loader_rejects_non_mapping(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- item", encoding="utf-8")
    loader = YamlChecklistLoader()
    try:
        loader.load(path)
    except ValueError as exc:
        assert "mapping" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for non-mapping YAML")


def test_yaml_loader_validate_schema_error(tmp_path: Path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
checklist:
  name: "Bad Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
""".strip(),
        encoding="utf-8",
    )
    loader = YamlChecklistLoader()
    issues = loader.validate(path)
    assert issues


def test_yaml_loader_validate_pydantic_error(tmp_path: Path):
    path = tmp_path / "invalid-severity.yaml"
    path.write_text(
        """
checklist:
  name: "Bad Severity"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
          check: "Do the thing"
          severity: "unknown"
""".strip(),
        encoding="utf-8",
    )
    loader = YamlChecklistLoader()
    issues = loader.validate(path)
    assert issues


def test_yaml_loader_load_raises_on_validation_errors(tmp_path: Path):
    path = tmp_path / "invalid-load.yaml"
    path.write_text(
        """
checklist:
  name: "Bad Checklist"
  version: "1.0.0"
  domain: "web"
  sections:
    - name: "Basics"
      items:
        - id: "item-1"
""".strip(),
        encoding="utf-8",
    )
    loader = YamlChecklistLoader()
    try:
        loader.load(path)
    except ValueError as exc:
        assert "validation failed" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError on invalid checklist load")
