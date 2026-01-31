from __future__ import annotations

from functools import lru_cache
from importlib import resources

from jinja2 import Environment, Template, select_autoescape

from tick.adapters.reporters.base import ReporterBase
from tick.adapters.reporters.utils import build_items_by_id
from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


class HtmlReporter(ReporterBase):
    content_type = "text/html"
    file_extension = "html"

    @staticmethod
    @lru_cache(maxsize=1)
    def _template() -> Template:
        template_text = resources.files("tick.templates.reports").joinpath(
            "report.html.j2"
        ).read_text(encoding="utf-8")
        env = Environment(autoescape=select_autoescape())
        return env.from_string(template_text)

    def generate(self, session: Session, checklist: Checklist) -> bytes:
        template = self._template()

        items_by_id = build_items_by_id(checklist)
        rows = []
        for response in session.responses:
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

        rendered = template.render(checklist=checklist, session=session, rows=rows)
        return rendered.encode("utf-8")
