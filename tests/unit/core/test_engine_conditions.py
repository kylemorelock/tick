from __future__ import annotations

import pytest

from tick.core.engine import _expand_items, _safe_eval_condition
from tick.core.utils import matrix_key


def test_safe_eval_condition_basic():
    variables = {"environment": "prod"}
    assert _safe_eval_condition("", variables) is True
    assert _safe_eval_condition("environment == 'prod'", variables) is True
    assert _safe_eval_condition("environment != 'prod'", variables) is False
    assert _safe_eval_condition("environment in ['prod', 'staging']", variables) is True
    assert _safe_eval_condition("environment in ['dev']", variables) is False
    assert (
        _safe_eval_condition("environment == 'prod' or environment == 'staging'", variables) is True
    )
    assert _safe_eval_condition("environment not in ['prod']", variables) is False
    assert _safe_eval_condition("not environment", {"environment": ""}) is True
    assert _safe_eval_condition("flag and enabled", {"flag": True, "enabled": True}) is True
    with pytest.raises(ValueError, match=r"Missing|missing"):
        _safe_eval_condition("missing == 'x'", variables)


def test_matrix_key_sorting():
    assert matrix_key(None) is None
    assert matrix_key({"b": 2, "a": 1}) == (("a", "1"), ("b", "2"))


def test_safe_eval_condition_invalid_expression():
    variables = {"environment": "prod"}
    with pytest.raises(ValueError, match=r"Unsupported|Invalid"):
        _safe_eval_condition("1 + 1", variables)
    with pytest.raises(ValueError, match=r"Unsupported|Invalid"):
        _safe_eval_condition("__import__('os')", variables)


def test_expand_items_respects_conditions(complex_checklist):
    items = _expand_items(complex_checklist, {"environment": "dev", "feature_flag": "on"})
    assert len(items) == 4
    items_prod = _expand_items(complex_checklist, {"environment": "prod", "feature_flag": "on"})
    assert len(items_prod) == 1
    items_feature_off = _expand_items(
        complex_checklist, {"environment": "dev", "feature_flag": "off"}
    )
    assert len(items_feature_off) == 3
