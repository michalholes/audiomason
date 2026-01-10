import pytest

from audiomason.pipeline_steps import DEFAULT_ORDER, resolve_pipeline_steps
from audiomason.util import AmConfigError


def test_default_order_when_not_set():
    cfg = {}
    assert resolve_pipeline_steps(cfg) == DEFAULT_ORDER


def test_custom_order_ok():
    cfg = {
        "pipeline_steps": [
            "unpack",
            "convert",
            "rename",
            "tags",
            "cover",
            "publish",
        ]
    }
    assert resolve_pipeline_steps(cfg) == cfg["pipeline_steps"]


def test_unknown_step_fails():
    cfg = {"pipeline_steps": ["unpack", "convert", "BOGUS"]}
    with pytest.raises(AmConfigError):
        resolve_pipeline_steps(cfg)


def test_duplicate_step_fails():
    cfg = {"pipeline_steps": ["unpack", "convert", "convert", "rename", "tags", "cover"]}
    with pytest.raises(AmConfigError):
        resolve_pipeline_steps(cfg)


def test_missing_required_step_fails():
    cfg = {"pipeline_steps": ["unpack", "convert", "rename"]}
    with pytest.raises(AmConfigError):
        resolve_pipeline_steps(cfg)
