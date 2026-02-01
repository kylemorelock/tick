from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

from jinja2 import Environment, Template, select_autoescape

from tick.adapters.reporters.base import ReporterBase
from tick.adapters.reporters.stats import compute_stats
from tick.adapters.reporters.utils import build_items_by_id, build_ordered_responses
from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


class HtmlReporter(ReporterBase):
    content_type = "text/html"
    file_extension = "html"

    def __init__(self, template_path: Path | None = None) -> None:
        """Initialize the HTML reporter.

        Args:
            template_path: Optional path to a custom Jinja2 template.
                          If None, uses the built-in template.
        """
        self._custom_template_path = template_path

    @staticmethod
    @lru_cache(maxsize=1)
    def _default_template() -> Template:
        """Load the built-in report template."""
        template_text = (
            resources.files("tick.templates.reports")
            .joinpath("report.html.j2")
            .read_text(encoding="utf-8")
        )
        env = Environment(autoescape=select_autoescape())
        return env.from_string(template_text)

    def _get_template(self) -> Template:
        """Get the template to use (custom or default)."""
        if self._custom_template_path:
            template_text = self._custom_template_path.read_text(encoding="utf-8")
            env = Environment(autoescape=select_autoescape())
            return env.from_string(template_text)
        return self._default_template()

    def generate(self, session: Session, checklist: Checklist) -> bytes:
        template = self._get_template()

        items_by_id = build_items_by_id(checklist)
        rows = []
        ordered_responses = build_ordered_responses(checklist, session)
        for response in ordered_responses:
            item = items_by_id.get(response.item_id)
            rows.append(
                {
                    "id": response.item_id,
                    "check": item.check if item else response.item_id,
                    "severity": item.severity.value if item else "unknown",
                    "result": response.result.value,
                    "notes": response.notes,
                    "evidence": list(response.evidence),
                    "matrix": response.matrix_context,
                }
            )

        stats = compute_stats(list(session.responses))

        rendered = template.render(
            checklist=checklist,
            session=session,
            rows=rows,
            stats=stats,
        )
        return rendered.encode("utf-8")
