"""E2E test fixtures and utilities.

These tests exercise complete CLI workflows as a user would experience them.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Callable

    ChecklistFactory = Callable[[str], Path]
    AnswersFactory = Callable[[str], Path]


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner for invoking commands."""
    return CliRunner()


@pytest.fixture
def checklist_file(tmp_path: Path) -> ChecklistFactory:
    """Factory for creating test checklist YAML files."""

    def _create(content: str, name: str = "checklist.yaml") -> Path:
        path = tmp_path / name
        path.write_text(content.strip(), encoding="utf-8")
        return path

    return _create


@pytest.fixture
def answers_file(tmp_path: Path) -> AnswersFactory:
    """Factory for creating test answers YAML files."""

    def _create(content: str, name: str = "answers.yaml") -> Path:
        path = tmp_path / name
        path.write_text(content.strip(), encoding="utf-8")
        return path

    return _create


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for session files."""
    out = tmp_path / "reports"
    out.mkdir(parents=True, exist_ok=True)
    return out


# Common checklist templates for testing


MINIMAL_CHECKLIST = """
checklist:
  name: "E2E Test Checklist"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Basic Section"
      items:
        - id: "item-1"
          check: "First check"
        - id: "item-2"
          check: "Second check"
"""

CHECKLIST_WITH_VARIABLES = """
checklist:
  name: "Variables Test"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "staging", "prod"]
      required: true
    feature:
      prompt: "Feature flag"
      default: "enabled"
  sections:
    - name: "Main"
      items:
        - id: "check-1"
          check: "Basic check"
"""

CHECKLIST_WITH_CONDITIONS = """
checklist:
  name: "Conditional Checklist"
  version: "1.0.0"
  domain: "test"
  variables:
    env:
      prompt: "Environment"
      options: ["dev", "prod"]
      required: true
  sections:
    - name: "Always"
      items:
        - id: "always-1"
          check: "This always runs"
    - name: "Dev Only"
      condition: "env == 'dev'"
      items:
        - id: "dev-1"
          check: "Dev-only check"
    - name: "Prod Only"
      condition: "env == 'prod'"
      items:
        - id: "prod-1"
          check: "Prod-only check"
"""

CHECKLIST_WITH_MATRIX = """
checklist:
  name: "Matrix Checklist"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Browser Tests"
      items:
        - id: "browser-test"
          check: "Test in browser"
          matrix:
            - browser: "chrome"
            - browser: "firefox"
            - browser: "safari"
"""

CHECKLIST_WITH_EVIDENCE = """
checklist:
  name: "Evidence Required"
  version: "1.0.0"
  domain: "test"
  sections:
    - name: "Security"
      items:
        - id: "sec-1"
          check: "Verify SSL certificate"
          severity: "critical"
          evidence_required: true
        - id: "sec-2"
          check: "Check firewall rules"
          severity: "high"
"""
