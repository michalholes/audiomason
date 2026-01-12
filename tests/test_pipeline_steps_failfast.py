import pytest

import audiomason.import_flow as imp
from audiomason.util import AmConfigError


def test_invalid_pipeline_steps_fail_before_fs(monkeypatch):
    touched = False

    def boom(*a, **k):
        nonlocal touched
        touched = True
        raise AssertionError("filesystem touched")

    monkeypatch.setattr(imp, "ensure_dir", boom)

    cfg = {"pipeline_steps": ["unpack", "convert", "BOGUS"]}

    with pytest.raises(AmConfigError):
        imp.run_import(cfg)

    assert touched is False
