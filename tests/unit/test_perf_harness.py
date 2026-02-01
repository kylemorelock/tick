from tick.core import perf
from tick.core.perf import PerfResult, run_harness


def test_perf_harness_runs(large_checklist_path):
    result = run_harness(large_checklist_path)

    assert isinstance(result, PerfResult)
    assert result.items > 0
    assert result.validate_seconds >= 0
    assert result.expand_seconds >= 0
    assert result.report_seconds >= 0


def test_perf_harness_formatting(large_checklist_path):
    result = run_harness(large_checklist_path)
    output = perf._format_result(result)
    assert "validate_seconds" in output
