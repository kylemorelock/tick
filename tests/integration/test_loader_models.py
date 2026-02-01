"""Integration tests for loader + models.

Tests that the YamlChecklistLoader correctly produces valid model instances.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tick.adapters.loaders.yaml_loader import YamlChecklistLoader
from tick.core.models.checklist import Checklist
from tick.core.models.enums import Severity


@pytest.mark.integration
class TestYamlLoaderModels:
    """Test YamlChecklistLoader produces valid Checklist models."""

    def test_loader_produces_valid_checklist(self, tmp_path: Path) -> None:
        """Test that loader parses YAML into valid Checklist model."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Integration Test"
  version: "2.1.0"
  domain: "api"
  metadata:
    author: "Test Team"
    tags: ["smoke", "regression"]
    estimated_time: "15 minutes"
  sections:
    - name: "Authentication"
      items:
        - id: "auth-1"
          check: "Verify login works"
          severity: "critical"
          guidance: "Use test credentials"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        assert isinstance(checklist, Checklist)
        assert checklist.name == "Integration Test"
        assert checklist.version == "2.1.0"
        assert checklist.domain == "api"
        assert checklist.metadata is not None
        assert checklist.metadata.author == "Test Team"
        assert "smoke" in checklist.metadata.tags
        assert len(checklist.sections) == 1
        assert checklist.sections[0].name == "Authentication"
        assert checklist.sections[0].items[0].severity == Severity.CRITICAL

    def test_loader_produces_valid_variables(self, tmp_path: Path) -> None:
        """Test that variables are parsed correctly."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    environment:
      prompt: "Select environment"
      required: true
      options: ["dev", "staging", "prod"]
    feature_flag:
      prompt: "Feature enabled?"
      default: "yes"
  sections:
    - name: "Checks"
      items:
        - id: "check-1"
          check: "Verify feature"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        assert len(checklist.variables) == 2
        assert "environment" in checklist.variables
        assert checklist.variables["environment"].required is True
        assert checklist.variables["environment"].options == ["dev", "staging", "prod"]
        assert checklist.variables["feature_flag"].default == "yes"
        assert checklist.variables["feature_flag"].required is False

    def test_loader_parses_conditions_and_matrix(self, tmp_path: Path) -> None:
        """Test that conditions and matrix are parsed correctly."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Complex Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Conditional Section"
      condition: "env == 'dev'"
      items:
        - id: "cond-item"
          check: "Dev-only check"
          condition: "env != 'prod'"
    - name: "Matrix Section"
      items:
        - id: "matrix-item"
          check: "Test in browser"
          matrix:
            - browser: "chrome"
              version: "latest"
            - browser: "firefox"
              version: "esr"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        # Check section condition
        assert checklist.sections[0].condition == "env == 'dev'"

        # Check item condition
        assert checklist.sections[0].items[0].condition == "env != 'prod'"

        # Check matrix
        matrix = checklist.sections[1].items[0].matrix
        assert matrix is not None
        assert len(matrix) == 2
        assert matrix[0]["browser"] == "chrome"
        assert matrix[1]["browser"] == "firefox"

    def test_loader_generates_consistent_checklist_id(self, tmp_path: Path) -> None:
        """Test that checklist_id is generated consistently."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "My Test Checklist"
  version: "3.2.1"
  domain: "web"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        checklist = loader.load(checklist_path)

        # checklist_id is name-version slugified
        expected_id = "my-test-checklist-3.2.1"
        assert checklist.checklist_id == expected_id

        # Loading again should produce same ID
        checklist2 = loader.load(checklist_path)
        assert checklist2.checklist_id == checklist.checklist_id


@pytest.mark.integration
class TestYamlLoaderValidation:
    """Test YamlChecklistLoader validation behavior."""

    def test_validate_returns_empty_for_valid_checklist(self, tmp_path: Path) -> None:
        """Test that validate() returns empty list for valid checklist."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Valid"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Section"
      items:
        - id: "item-1"
          check: "Check"
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        issues = loader.validate(checklist_path)
        assert issues == []

    def test_validate_reports_missing_required_fields(self, tmp_path: Path) -> None:
        """Test that validate() reports missing required fields."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Missing Fields"
  # Missing: version, domain, sections
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        issues = loader.validate(checklist_path)
        assert len(issues) > 0

    def test_load_raises_on_validation_errors(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError for invalid checklist."""
        checklist_path = tmp_path / "checklist.yaml"
        checklist_path.write_text(
            """
checklist:
  name: "Invalid"
  # Missing required fields
""",
            encoding="utf-8",
        )

        loader = YamlChecklistLoader()
        with pytest.raises(ValueError, match="validation failed"):
            loader.load(checklist_path)
