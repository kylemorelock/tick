"""Shared statistics computation for reporters."""

from __future__ import annotations

from tick.core.models.session import Response


def compute_stats(responses: list[Response]) -> dict[str, int]:
    """Compute summary statistics from session responses.

    Returns a dict with keys: pass, fail, skip, na, total
    """
    stats = {"pass": 0, "fail": 0, "skip": 0, "na": 0, "total": 0}
    for response in responses:
        stats[response.result.value] += 1
        stats["total"] += 1
    return stats
