from __future__ import annotations

import sys


def _write_min_config(tmp_path, *, banner: bool) -> str:
    # Minimal config to satisfy CLI/config loader while staying deterministic.
    # Use explicit absolute paths to avoid any environment-dependent defaults.
    cfgp = tmp_path / "configuration.yaml"
    cfgp.write_text(
        (
            f"version-banner: {str(banner).lower()}\n"
            "publish: no\n"
            "clean_inbox: no\n"
            "paths:\n"
            f"  inbox: {tmp_path / 'abooksinbox'}\n"
            f"  stage: {tmp_path / '_am_stage'}\n"
            f"  output: {tmp_path / 'abooks'}\n"
            f"  ready: {tmp_path / 'abooks_ready'}\n"
            f"  archive: {tmp_path / 'abooks_archive'}\n"
            f"  cache: {tmp_path / 'am_cache'}\n"
        ),
        encoding="utf-8",
    )
    return str(cfgp)


def _make_contract_dirs(tmp_path) -> None:
    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_archive").mkdir(parents=True, exist_ok=True)
    (tmp_path / "am_cache").mkdir(parents=True, exist_ok=True)


def test_version_banner_shows_when_enabled(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=True)

    from audiomason.version import __version__
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--config", cfg, "cache", "gc"])
    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert __version__ in out


def test_version_banner_suppressed_on_quiet(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=True)

    from audiomason.version import __version__
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--quiet", "--config", cfg, "cache", "gc"])
    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert __version__ not in out


def test_version_banner_still_present_on_quiet_json(monkeypatch, tmp_path, capsys):
    # User requirement: --quiet suppresses banner unless --json is enabled.
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=True)

    from audiomason.version import __version__
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--quiet", "--json", "--config", cfg, "cache", "gc"])
    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert __version__ in out
