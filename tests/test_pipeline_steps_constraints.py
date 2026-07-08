import pytest

from audiomason.pipeline_steps import resolve_pipeline_steps
from audiomason.util import AmConfigError


def test_process_step_cannot_be_between_stage_steps():
    cfg = {
        "pipeline_steps": [
            "unpack",
            "convert",
            "cover",  # invalid: PROCESS step before chapters/split
            "chapters",
            "split",
            "tags",
            "rename",
            "publish",
        ]
    }
    with pytest.raises(AmConfigError):
        resolve_pipeline_steps(cfg)


def test_process_reorder_is_allowed_after_stage():
    cfg = {
        "pipeline_steps": [
            "unpack",
            "convert",
            "chapters",
            "split",
            "cover",
            "tags",
            "rename",
            "publish",
        ]
    }
    assert resolve_pipeline_steps(cfg) == cfg["pipeline_steps"]
