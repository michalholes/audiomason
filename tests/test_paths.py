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


def test_paths_cfg_legacy_keys_propagate(tmp_path, monkeypatch):
    """Issue #123 regression: legacy config keys must still affect runtime path resolution."""
    import importlib

    monkeypatch.setenv("AUDIOMASON_DATA_ROOT", str(tmp_path / "_ignored_base"))
    import audiomason.paths as paths

    importlib.reload(paths)

    inbox = tmp_path / "inbox"
    staging = tmp_path / "staging"
    library = tmp_path / "library"
    cache = tmp_path / "cache"
    trash = tmp_path / "trash"

    cfg = {
        "paths": {
            "inbox": str(inbox),
            "staging": str(staging),
            "library": str(library),
            "cache": str(cache),
            "trash": str(trash),
        }
    }

    # Must validate without falling back to ~/.local/share/audiomason defaults.
    paths.validate_paths_contract(cfg)

    assert paths.get_drop_root(cfg) == inbox
    assert paths.get_stage_root(cfg) == staging
    # Legacy: library is accepted as the effective output root when output/ready are not specified.
    assert paths.get_output_root(cfg) == library
    # Legacy: library is also accepted as the archive root when archive is not specified.
    assert paths.get_archive_root(cfg) == library
    assert paths.get_cache_root(cfg) == cache


def test_paths_cfg_outside_root_allowed_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIOMASON_DATA_ROOT", str(tmp_path))
    import importlib

    import audiomason.paths as paths

    importlib.reload(paths)
    other = tmp_path.parent / "data_root_elsewhere"
    cfg = {"paths": {"inbox": str(other / "abooksinbox")}}
    paths.validate_paths_contract(cfg)
