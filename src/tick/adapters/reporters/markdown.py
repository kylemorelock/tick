from __future__ import annotations

from tick.adapters.reporters.base import ReporterBase
from tick.adapters.reporters.utils import build_items_by_id
from tick.core.models.checklist import Checklist
from tick.core.models.session import Session


def _escape_cell(value: str) -> str:
    escaped = value.replace("|", "\\|")
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    return escaped.replace("\n", "<br>")


class MarkdownReporter(ReporterBase):
    content_type = "text/markdown"
    file_extension = "md"

    def generate(self, session: Session, checklist: Checklist) -> bytes:
        items_by_id = build_items_by_id(checklist)
        lines = [
            f"# {checklist.name}",
            "",
            f"Version: {checklist.version}",
            f"Domain: {checklist.domain}",
            "",
            "## Results",
            "",
            "| ID | Check | Severity | Result | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]

        for response in session.responses:
            item = items_by_id.get(response.item_id)
            check = item.check if item else response.item_id
            severity = item.severity.value if item else "unknown"
            notes = response.notes or ""
            if response.matrix_context:
                context = ", ".join(f"{key}={value}" for key, value in response.matrix_context.items())
                check = f"{check} ({context})"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_cell(response.item_id),
                        _escape_cell(check),
                        _escape_cell(severity),
                        _escape_cell(response.result.value),
                        _escape_cell(notes),
                    ]
                )
                + " |"
            )

        lines.append("")
        return "\n".join(lines).encode("utf-8")
