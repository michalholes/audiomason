import pytest

from audiomason.pipeline_steps import resolve_pipeline_steps
from audiomason.util import AmConfigError


def test_cover_before_convert_fails():
    cfg = {
        "pipeline_steps": [
            "unpack",
            "cover",
            "convert",
            "chapters",
            "split",
            "tags",
            "rename",
            "publish",
        ]
    }
    with pytest.raises(AmConfigError):
        resolve_pipeline_steps(cfg)
