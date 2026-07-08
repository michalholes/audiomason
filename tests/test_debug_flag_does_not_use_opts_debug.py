import pytest

import audiomason.import_flow as imp
import audiomason.state as state


def test_debug_uses_state_debug_not_opts_debug(monkeypatch, tmp_path):
    # Ensure DEBUG exists and is True
    monkeypatch.setattr(state, "DEBUG", True, raising=False)

    # Stop before filesystem side-effects
    def boom(*a, **k):
        raise AssertionError("stop before fs")

    monkeypatch.setattr(imp, "ensure_dir", boom)

    cfg = {"pipeline_steps": ["unpack", "convert", "rename", "tags", "cover", "publish"]}

    with pytest.raises(AssertionError, match="stop before fs"):
        imp.run_import(cfg)
