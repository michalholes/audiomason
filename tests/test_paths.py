import importlib
from pathlib import Path


def test_paths_default_are_paths():
    import audiomason.paths as paths

    assert isinstance(paths.DROP_ROOT, Path)
    assert isinstance(paths.OUTPUT_ROOT, Path)


def test_paths_override_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIOMASON_DATA_ROOT", str(tmp_path))
    import audiomason.paths as paths

    importlib.reload(paths)
    assert paths.get_drop_root({}) == tmp_path / "abooksinbox"
    assert paths.get_output_root({}) == tmp_path / "abooks_ready"
    paths.validate_paths_contract({})


def test_paths_cfg_outside_root_allowed_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIOMASON_DATA_ROOT", str(tmp_path))
    import importlib

    import audiomason.paths as paths

    importlib.reload(paths)
    other = tmp_path.parent / "data_root_elsewhere"
    cfg = {"paths": {"inbox": str(other / "abooksinbox")}}
    paths.validate_paths_contract(cfg)
