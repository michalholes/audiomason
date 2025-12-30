from pathlib import Path
import os
import importlib

def test_paths_default_are_paths():
    import audiomason.paths as paths
    assert isinstance(paths.DROP_ROOT, Path)
    assert isinstance(paths.OUTPUT_ROOT, Path)

def test_paths_override_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    import audiomason.paths as paths
    importlib.reload(paths)
    assert paths.DROP_ROOT == tmp_path / "abooksinbox"
    assert paths.OUTPUT_ROOT == tmp_path / "abooks_ready"
